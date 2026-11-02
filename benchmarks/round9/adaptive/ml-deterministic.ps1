# Invoke only through queue-ml-deterministic.ps1 under the shared exclusive bench lock.
$ErrorActionPreference = 'Stop'
$lab = 'C:\Users\User\Work\mink-lab'
$src = 'C:\Users\User\Work\mink-wt\integration'
$build = 'C:\Users\User\Work\mink-build\integration-cuda'
$out = "$lab\results\round9\ml-deterministic-check"
$expected = 'f3f74919a64bede57fab7d5f303e94ca188c931a'
$expectedHash = 'F66BB23A370DA9C7F4AF3BB5647C34337AE49A2BF7A093765B482280020DB35A'
if (Test-Path -LiteralPath "$out\receipt.json") { throw 'Existing deterministic receipt; inspect it rather than overwriting experiment' }
New-Item -ItemType Directory -Force -Path $out | Out-Null
. "$lab\tools\mink-env.ps1" -Quiet
$env:CUDA_MODULE_LOADING = 'EAGER'
$env:CUBLAS_WORKSPACE_CONFIG = ':4096:8'
Set-Location -LiteralPath $build
$exe = "$build\ml_representations.exe"
$head = (& git -C $src rev-parse HEAD).Trim()
if ($head -ne $expected) { throw "Source changed: $head" }
if (& git -C $src diff --name-only HEAD) { throw 'Tracked source is dirty' }
$hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
if ($hash -ne $expectedHash) { throw 'Executable changed since six-round experiment' }
$receipt = [ordered]@{ status = 'running'; started = (Get-Date -Format o); head = $head;
    executable = $exe; executable_sha256 = $hash; budgets_mb = @(-1,32,0);
    deterministic_algorithms = $true; deterministic_warn_only = $true; fused_apply_requested = $true;
    effective_apply_path = 'existing ATen per-slot fallback because deterministicAlgorithms is true';
    purpose = 'Numerical cache-policy comparison only: one process per arm, no timing claims';
    cuda_module_loading = $env:CUDA_MODULE_LOADING; cublas_workspace_config = $env:CUBLAS_WORKSPACE_CONFIG;
    runs = @() }
function Save { $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$out\receipt.json" }
Save
try {
    for ($arm = 0; $arm -lt 3; $arm++) {
        $budget = $receipt.budgets_mb[$arm]
        $stem = "adaptive_b$arm"
        $benchArgs = @('--method','adaptive','--seed','1','--device','cuda',
            '--train-per-class','30','--test-per-class','20','--epochs','3','--batch','16',
            '--points','2048','--data-seed','2026','--profile-steps','0',
            '--kmap-part-reuse-mb','512','--kmap-part-device-mb',"$budget",
            '--fused-apply','1','--deterministic','1','--output',"$out\$stem.json")
        & $exe @benchArgs *> "$out\$stem.log"
        $code = $LASTEXITCODE
        $receipt.runs += [ordered]@{ arm = $arm; budget_mb = $budget; exit = $code; arguments = $benchArgs; completed = (Get-Date -Format o) }
        Save
        if ($code -ne 0) { throw "Deterministic $stem failed: $code" }
        $row = Get-Content -LiteralPath "$out\$stem.json" -Raw | ConvertFrom-Json
        if ($row.kmap_part_device_mb -ne $budget -or @($row.curve).Count -ne 3) { throw "Invalid result: $stem" }
        if ($budget -ge 0 -and ($row.kmap_part_device_bytes -gt $budget * 1048576 -or $row.kmap_part_device_peak_bytes -gt $budget * 1048576)) { throw "Budget exceeded: $stem" }
    }
    if ((Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash -ne $hash) { throw 'Executable changed during check' }
    if ((& git -C $src rev-parse HEAD).Trim() -ne $head) { throw 'Source changed during check' }
    if (& git -C $src diff --name-only HEAD) { throw 'Tracked source changed during check' }
    $receipt.status = 'passed'
} catch {
    $receipt.status = 'failed'
    $receipt.error = $_.Exception.Message
} finally {
    $receipt.completed = (Get-Date -Format o)
    Save
}
if ($receipt.status -ne 'passed') { throw $receipt.error }
