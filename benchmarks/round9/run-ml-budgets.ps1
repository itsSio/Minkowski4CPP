param(
    [Parameter(Mandatory)][string]$ExpectedHead,
    [string]$Tag = 'ml-budgets',
    [string]$Budgets = '-1,32,0',
    [int]$Rounds = 6
)
# Invoke only under with-lock.ps1 -Kind bench.
$ErrorActionPreference = 'Stop'
$lab = 'C:\Users\User\Work\mink-lab'
$src = 'C:\Users\User\Work\mink-wt\integration'
$build = 'C:\Users\User\Work\mink-build\integration-cuda'
$out = Join-Path $lab "results\round9\$Tag"
New-Item -ItemType Directory -Force -Path $out | Out-Null
. "$lab\tools\mink-env.ps1" -Quiet
$env:CUDA_MODULE_LOADING = 'EAGER'
$env:CUBLAS_WORKSPACE_CONFIG = ':4096:8'
Set-Location -LiteralPath $build
$head = (& git -C $src rev-parse HEAD).Trim()
if ($head -ne $ExpectedHead) { throw "Unexpected source $head" }
if (& git -C $src diff --name-only HEAD) { throw 'Tracked source is dirty' }
$values = @($Budgets -split ',' | ForEach-Object { [double]$_ })
if ($values.Count -ne 3 -or $Rounds % 6 -ne 0) { throw 'Use three arms and a multiple of six rounds for balanced order' }
$exe = "$build\ml_representations.exe"
$hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
$receipt = [ordered]@{ status = 'running'; started = (Get-Date -Format o); head = $head;
    executable = $exe; executable_sha256 = $hash; budgets_mb = $values; rounds = $Rounds;
    cuda_module_loading = $env:CUDA_MODULE_LOADING; cublas_workspace_config = $env:CUBLAS_WORKSPACE_CONFIG;
    deterministic_algorithms = $false; fused_apply_requested = $true;
    rationale = 'Exercise the default fused CUDA apply path; deterministic mode bypasses it. Seeds fixed, atomic summation may vary.'; runs = @() }
function Save { $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$out\receipt.json" }
Save
try {
    & pwsh -NoProfile -File "$lab\results\bridge-ml\r3\hostload.ps1" -Log "$out\hostload.log" -Tag before -Sec 3
    $orders = @(@(0,1,2), @(2,1,0), @(1,2,0), @(0,2,1), @(2,0,1), @(1,0,2))
    for ($round = 1; $round -le $Rounds; $round++) {
        foreach ($arm in $orders[($round - 1) % 6]) {
            $stem = "adaptive_b${arm}_r$round"
            $benchArgs = @('--method','adaptive','--seed','1','--device','cuda',
                '--train-per-class','30','--test-per-class','20','--epochs','3','--batch','16',
                '--points','2048','--data-seed','2026','--profile-steps','0',
                '--kmap-part-reuse-mb','512','--kmap-part-device-mb',"$($values[$arm])",
                '--fused-apply','1','--deterministic','0','--output',"$out\$stem.json")
            & $exe @benchArgs *> "$out\$stem.log"
            $code = $LASTEXITCODE
            $receipt.runs += [ordered]@{ round = $round; arm = $arm; budget_mb = $values[$arm]; exit = $code; arguments = $benchArgs; completed = (Get-Date -Format o) }
            Save
            if ($code -ne 0) { throw "ML $stem failed: $code" }
            $data = Get-Content -LiteralPath "$out\$stem.json" -Raw | ConvertFrom-Json
            if (@($data.curve).Count -ne 3 -or $data.peak_cuda_alloc_mb_train -le 0) { throw "Incomplete ML metrics: $stem" }
            if ($null -eq $data.kmap_part_device_bytes) { throw "Budget instrumentation missing: $stem" }
            if ($values[$arm] -ge 0 -and $data.kmap_part_device_bytes -gt $values[$arm] * 1048576) { throw "Retained device budget exceeded: $stem" }
        }
        & pwsh -NoProfile -File "$lab\results\bridge-ml\r3\hostload.ps1" -Log "$out\hostload.log" -Tag "after-round-$round" -Sec 2
    }
    if ((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ne $hash) { throw 'Executable changed during ML run' }
    if ((& git -C $src rev-parse HEAD).Trim() -ne $head) { throw 'Source changed during ML run' }
    $receipt.status = 'passed'
} catch {
    $receipt.status = 'failed'
    $receipt.error = $_.Exception.Message
} finally {
    $receipt.completed = (Get-Date -Format o)
    Save
}
if ($receipt.status -ne 'passed') { throw $receipt.error }
