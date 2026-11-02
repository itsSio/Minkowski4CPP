param(
    [Parameter(Mandatory)][string]$Tag,
    [Parameter(Mandatory)][string]$ExpectedHead,
    [ValidateSet('fused-ssim','fused-adam','fused-gather','all-fusions')][string]$Feature = 'fused-ssim',
    [int]$Rounds = 10,
    [string]$Sizes = '512,1024',
    [int]$SettleSeconds = 60
)
$ErrorActionPreference = 'Stop'
$lab = 'C:\Users\User\Work\mink-lab'
$src = 'C:\Users\User\Work\mink-wt\integration'
$build = 'C:\Users\User\Work\mink-build\integration-cuda'
$out = Join-Path $lab "results\round9\$Tag"
New-Item -ItemType Directory -Path $out -Force | Out-Null
. "$lab\tools\mink-env.ps1" -Quiet
Set-Location -LiteralPath $build
$head = (& git -C $src rev-parse HEAD).Trim()
if ($head -ne $ExpectedHead) { throw "Expected source $ExpectedHead; got $head" }
if (& git -C $src diff --name-only HEAD) { throw 'Tracked source is dirty' }
$exe = "$build\gaussian_render_bench.exe"
$hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
$ply = "$src\tests\data\test.ply"
$receipt = [ordered]@{
    status = 'running'; started = (Get-Date -Format o); head = $head;
    executable = $exe; executable_sha256 = $hash;
    input = $ply; input_sha256 = (Get-FileHash -LiteralPath $ply -Algorithm SHA256).Hash;
    feature = $Feature; rounds = $Rounds; sizes = $Sizes; warmup = 3; iterations = 10;
    hardware = (& nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader);
    runs = @()
}
function Save { $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$out\receipt.json" }
Save
try {
    $settleUntil = (Get-Date).AddSeconds($SettleSeconds)
    $receipt.settling_cpu_percent = @()
    do {
        $counter = Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 3 -ErrorAction SilentlyContinue
        if (-not $counter) { break }
        $cpuLoad = ($counter.CounterSamples.CookedValue | Measure-Object -Average).Average
        $receipt.settling_cpu_percent += $cpuLoad
        Save
        if ($cpuLoad -lt 30 -or (Get-Date) -ge $settleUntil) { break }
        Start-Sleep -Seconds 3
    } while ($true)
    & pwsh -NoProfile -File "$lab\results\bridge-ml\r3\hostload.ps1" -Log "$out\hostload.log" -Tag before -Sec 3
    for ($round = 1; $round -le $Rounds; $round++) {
        $arms = if ($round % 2) { @(0, 1) } else { @(1, 0) }
        foreach ($arm in $arms) {
            $stem = "train_a${arm}_r$round"
            $benchArgs = @('--input', $ply, '--counts', '0', '--sizes', $Sizes, '--devices', 'cuda', '--warmup', '3', '--iterations', '10', '--train', '--label', "$Tag-$stem", '--output', "$out\$stem.json")
            $features = if ($Feature -eq 'all-fusions') { @('fused-projection','fused-tiles','fused-ssim','fused-adam','fused-gather') } else { @($Feature) }
            foreach ($toggle in $features) { $benchArgs += @("--$toggle", "$arm") }
            & $exe @benchArgs *> "$out\$stem.txt"
            $code = $LASTEXITCODE
            $receipt.runs += [ordered]@{ round = $round; arm = $arm; exit = $code; arguments = $benchArgs; completed = (Get-Date -Format o) }
            Save
            if ($code -ne 0) { throw "Benchmark $stem failed: $code" }
            $data = Get-Content -LiteralPath "$out\$stem.json" -Raw | ConvertFrom-Json
            if (@($data.records).Count -ne ($Sizes -split ',').Count) { throw "Missing records in $stem" }
            foreach ($record in $data.records) {
                if ($record.train_median_ms -le 0 -or @($record.train_ms).Count -ne 10) { throw "Missing train samples in $stem" }
            }
        }
        & pwsh -NoProfile -File "$lab\results\bridge-ml\r3\hostload.ps1" -Log "$out\hostload.log" -Tag "after-round-$round" -Sec 2
    }
    if ((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ne $hash) { throw 'Executable changed during A/B' }
    if ((& git -C $src rev-parse HEAD).Trim() -ne $head) { throw 'Source changed during A/B' }
    $receipt.status = 'passed'
} catch {
    $receipt.status = 'failed'
    $receipt.error = $_.Exception.Message
} finally {
    $receipt.completed = (Get-Date -Format o)
    Save
}
if ($receipt.status -ne 'passed') { throw $receipt.error }
