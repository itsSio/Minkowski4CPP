$ErrorActionPreference='Stop'
. 'C:\Users\User\Work\mink-lab\tools\mink-env.ps1' -Cpu:$('cpu' -eq 'cpu') -Quiet
$env:CUDA_MODULE_LOADING='EAGER'
& ctest --test-dir 'C:\Users\User\Work\mink-build\integration-cpu' --parallel 1 --verbose --output-on-failure --timeout 420 --output-junit 'C:\Users\User\Work\mink-lab\results\round10\integration-final\ctest-cpu.xml' *> 'C:\Users\User\Work\mink-lab\results\round10\integration-final\ctest-cpu.log'
exit $LASTEXITCODE
