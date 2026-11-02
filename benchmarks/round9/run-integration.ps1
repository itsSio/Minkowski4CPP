param(
    [string]$Tag = 'integration-8b',
    [Parameter(Mandatory)][string]$ExpectedHead,
    [string[]]$Kinds = @('cpu', 'cuda')
)
$ErrorActionPreference = 'Stop'
$lab = 'C:\Users\User\Work\mink-lab'
$src = 'C:\Users\User\Work\mink-wt\integration'
$out = Join-Path $lab "results\round9\$Tag"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$head = (& git -C $src rev-parse HEAD).Trim()
if (-not $head.StartsWith($ExpectedHead)) { throw "Expected $ExpectedHead; got $head" }
$receipt = [ordered]@{ started = (Get-Date -Format o); source = $src; head = $head; tag = $Tag; status = 'running'; configurations = @() }
function Save { $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$out\receipt.json" }
function Note($message) { "$(Get-Date -Format o) $message" | Tee-Object -FilePath "$out\pipeline.log" -Append }
Save
try {
    foreach ($kind in $Kinds) {
        if ((& git -C $src rev-parse HEAD).Trim() -ne $head) { throw 'Source HEAD changed during integration' }
        if (& git -C $src diff --name-only HEAD) { throw 'Tracked source is dirty' }
        $build = "C:\Users\User\Work\mink-build\integration-$kind"
        $run = [ordered]@{ kind = $kind; build = $build; started = (Get-Date -Format o); build_exit = $null; test_exit = $null; binaries = @() }
        $receipt.configurations += $run
        Save
        Note "$kind build start $head"
        $buildArgs = @('-NoProfile', '-File', "$lab\tools\mink-build.ps1", '-Src', $src, '-Build', $build, '-Who', 'integration-r9')
        if ($kind -eq 'cpu') { $buildArgs += '-Cpu' }
        & pwsh @buildArgs *> "$out\build-$kind.log"
        $run.build_exit = $LASTEXITCODE
        Save
        if ($LASTEXITCODE -ne 0) { throw "$kind build failed: $LASTEXITCODE" }
        foreach ($name in 'adaptive_tests', 'gaussian_tests', 'core_tests', 'memory_growth_tests', 'gaussian_render_bench', 'ml_representations') {
            $file = Get-Item -LiteralPath "$build\$name.exe"
            $run.binaries += [ordered]@{ name = $name; sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash; bytes = $file.Length; modified = $file.LastWriteTime.ToString('o') }
        }
        Save
        $cpuArg = if ($kind -eq 'cpu') { '-Cpu' } else { '' }
        $cmd = ". '$lab\tools\mink-env.ps1' $cpuArg -Quiet; Set-Location '$build'; ctest --test-dir '$build' --verbose --output-on-failure --timeout 420 --output-junit '$out\ctest-$kind.xml' *> '$out\ctest-$kind.txt'; exit `$LASTEXITCODE"
        Note "$kind CTest start"
        & pwsh -NoProfile -File "$lab\tools\with-lock.ps1" -Kind gpu -Who integration-r9 -Command $cmd *> "$out\lock-$kind.log"
        $run.test_exit = $LASTEXITCODE
        $run.completed = (Get-Date -Format o)
        Save
        if ($LASTEXITCODE -ne 0) { throw "$kind CTest failed: $LASTEXITCODE" }
        if ((& git -C $src rev-parse HEAD).Trim() -ne $head) { throw 'Source HEAD changed during validation' }
        Note "$kind passed"
    }
    $receipt.status = 'passed'
} catch {
    $receipt.status = 'failed'
    $receipt.error = $_.Exception.Message
    Note "FAILED: $_"
} finally {
    $receipt.completed = (Get-Date -Format o)
    Save
}
if ($receipt.status -ne 'passed') { exit 1 }
Note 'RUN-DONE'
