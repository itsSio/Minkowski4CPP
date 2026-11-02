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
