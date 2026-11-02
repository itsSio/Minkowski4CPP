$ErrorActionPreference='Stop'
$lab='C:\Users\User\Work\mink-lab'
$source='C:\Users\User\Work\mink-wt\integration'
$build='C:\Users\User\Work\mink-build\integration-cuda'
$expected='a67f671f4aa3a003751e3d06af85d2b9b8b459e5'
$original="$lab\results\round10\integration-final"
$out="$original\lazy-retry"
if(Test-Path -LiteralPath $out){throw 'Refuse overwriting previous native recovery evidence'}
New-Item -ItemType Directory -Path $out | Out-Null
Write-Output "$(Get-Date -Format o) waiting for original full CTest orchestrator28060"
Wait-Process -Id 28060 -ErrorAction SilentlyContinue
$previous=Get-Content -LiteralPath "$original\receipt.json" -Raw | ConvertFrom-Json
if($previous.source -ne $expected -or $previous.status -eq 'running'){throw 'Original validation identity/status is incomplete'}
foreach($file in @('receipt.json','ctest-cuda.xml','ctest-cuda.log')){
  Copy-Item -LiteralPath "$original\$file" -Destination "$out\eager-$file" -ErrorAction Stop
}
$receipt=[ordered]@{status='waiting_gpu_lock';source=$expected;started=(Get-Date -Format o);loading='LAZY';timeout_seconds=420;original_status=$previous.status;original_error=$previous.error;ctest_exit=$null}
function Save{
  $content=$receipt|ConvertTo-Json -Depth 10
  [IO.File]::WriteAllText("$out\receipt.new.json",$content)
  for($n=0;$n -lt 20;$n++){
    try{Move-Item -LiteralPath "$out\receipt.new.json" -Destination "$out\receipt.json" -Force;return}
    catch{if($n -eq 19){throw};Start-Sleep -Milliseconds 100}
  }
}
Save
$runner="$out\run-ctest.ps1"
@'
$ErrorActionPreference='Stop'
$out=$PSScriptRoot
$source='C:\Users\User\Work\mink-wt\integration'
$build='C:\Users\User\Work\mink-build\integration-cuda'
$expected='a67f671f4aa3a003751e3d06af85d2b9b8b459e5'
if((& git -C $source rev-parse HEAD).Trim() -ne $expected -or (& git -C $source diff --name-only HEAD)){throw 'Source changed before LAZY retry'}
. 'C:\Users\User\Work\mink-lab\tools\mink-env.ps1' -Quiet
$env:CUDA_MODULE_LOADING='LAZY'
& nvidia-smi --query-gpu=timestamp,name,driver_version,pstate,utilization.gpu,memory.used,memory.free --format=csv *> "$out\gpu-before.csv"
$bins=@('adaptive_tests','adaptive_split_tests','gaussian_tests','core_tests','ml_representations','point_dataset_tests','benchmark_memory_tests')
$before=@($bins|ForEach-Object{[ordered]@{name=$_;sha256=(Get-FileHash -LiteralPath "$build\$_.exe").Hash}})
$before|ConvertTo-Json -Depth 5|Set-Content "$out\binaries-before.json"
Write-Output "$(Get-Date -Format o) running complete CUDA CTest with LAZY loading"
& ctest --test-dir $build --parallel 1 --verbose --output-on-failure --timeout 420 --output-junit "$out\ctest-cuda.xml" *> "$out\ctest-cuda.log"
$code=$LASTEXITCODE
& nvidia-smi --query-gpu=timestamp,name,driver_version,pstate,utilization.gpu,memory.used,memory.free --format=csv *> "$out\gpu-after.csv"
$after=@($bins|ForEach-Object{[ordered]@{name=$_;sha256=(Get-FileHash -LiteralPath "$build\$_.exe").Hash}})
$after|ConvertTo-Json -Depth 5|Set-Content "$out\binaries-after.json"
if(($before|ConvertTo-Json -Compress) -ne ($after|ConvertTo-Json -Compress)){throw 'Binary identities changed during LAZY retry'}
if((& git -C $source rev-parse HEAD).Trim() -ne $expected -or (& git -C $source diff --name-only HEAD)){throw 'Source changed during LAZY retry'}
Write-Output "$(Get-Date -Format o) full LAZY CTest exit$code"
exit $code
'@|Set-Content -LiteralPath $runner
try{
  & pwsh -NoProfile -File "$lab\tools\with-lock.ps1" -Kind gpu -Who integration-lazy-full-retry -Command "pwsh -NoProfile -File $runner"
  $receipt.ctest_exit=$LASTEXITCODE
  $receipt.status=if($LASTEXITCODE -eq 0){'passed'}else{'failed'}
}catch{$receipt.status='failed';$receipt.error=$_.Exception.Message}
$receipt.completed=(Get-Date -Format o);Save
Write-Output "$(Get-Date -Format o) $($receipt.status)"
if($receipt.status -ne 'passed'){exit 1}
