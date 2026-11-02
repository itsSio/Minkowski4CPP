$ErrorActionPreference='Stop'
$lab='C:\Users\User\Work\mink-lab'
$source='C:\Users\User\Work\mink-wt\integration'
$expected='a67f671f4aa3a003751e3d06af85d2b9b8b459e5'
$out="$lab\results\round10\integration-final"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$receipt=[ordered]@{status='running';source=$expected;started=(Get-Date -Format o);configurations=@()}
function Save {
  $json=$receipt | ConvertTo-Json -Depth 10
  [IO.File]::WriteAllText("$out\receipt.new.json",$json)
  for($retry=0;$retry -lt 20;$retry++) {
    try { Move-Item -LiteralPath "$out\receipt.new.json" -Destination "$out\receipt.json" -Force; return }
    catch { if($retry -eq 19){throw}; Start-Sleep -Milliseconds 100 }
  }
}
function CheckSource {
  if ((& git -C $source rev-parse HEAD).Trim() -ne $expected -or (& git -C $source diff --name-only HEAD)) {
    throw 'Integration source changed during validation'
  }
}
Save
try {
  CheckSource
  foreach($kind in @('cpu','cuda')) {
    Write-Output "$(Get-Date -Format o) building $kind"
    $build="C:\Users\User\Work\mink-build\integration-$kind"
    $args=@('-NoProfile','-File',"$lab\tools\mink-build.ps1",'-Src',$source,'-Build',$build,'-Jobs','2','-Who',"round10-integrated-$kind")
    if($kind -eq 'cpu'){$args+='-Cpu'}
    & pwsh @args *> "$out\build-$kind.log"
    if($LASTEXITCODE -ne 0){throw "$kind build failed"}
    CheckSource
    Write-Output "$(Get-Date -Format o) testing $kind"
    $testScript="$out\ctest-$kind.ps1"
    @"
`$ErrorActionPreference='Stop'
. '$lab\tools\mink-env.ps1' -Cpu:`$('$kind' -eq 'cpu') -Quiet
`$env:CUDA_MODULE_LOADING='EAGER'
& ctest --test-dir '$build' --parallel 1 --verbose --output-on-failure --timeout 420 --output-junit '$out\ctest-$kind.xml' *> '$out\ctest-$kind.log'
exit `$LASTEXITCODE
"@ | Set-Content -LiteralPath $testScript
    & pwsh -NoProfile -File "$lab\tools\with-lock.ps1" -Kind gpu -Who "round10-integrated-$kind-tests" -Command "pwsh -NoProfile -File $testScript"
    if($LASTEXITCODE -ne 0){throw "$kind CTest failed"}
    $bins=@('adaptive_tests','adaptive_split_tests','gaussian_tests','core_tests','ml_representations','point_dataset_tests','benchmark_memory_tests') | ForEach-Object {
      $path="$build\$_.exe"
      [ordered]@{name=$_;sha256=(Get-FileHash -LiteralPath $path).Hash}
    }
    $receipt.configurations += [ordered]@{kind=$kind;build_exit=0;ctest_exit=0;binaries=$bins;completed=(Get-Date -Format o)}
    CheckSource
    Save
  }
  $receipt.status='passed'
} catch {$receipt.status='failed';$receipt.error=$_.Exception.Message}
$receipt.completed=(Get-Date -Format o); Save
Write-Output "$(Get-Date -Format o) $($receipt.status) $($receipt.error)"
if($receipt.status -ne 'passed'){exit 1}
