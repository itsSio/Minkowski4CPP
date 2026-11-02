$ErrorActionPreference='Stop'
. 'C:\Users\User\Work\mink-lab\tools\mink-env.ps1' -Cpu:$('cuda' -eq 'cpu') -Quiet
$env:CUDA_MODULE_LOADING='EAGER'
& ctest --test-dir 'C:\Users\User\Work\mink-build\integration-cuda' --parallel 1 --verbose --output-on-failure --timeout 420 --output-junit 'C:\Users\User\Work\mink-lab\results\round10\integration-final\ctest-cuda.xml' *> 'C:\Users\User\Work\mink-lab\results\round10\integration-final\ctest-cuda.log'
exit $LASTEXITCODE
