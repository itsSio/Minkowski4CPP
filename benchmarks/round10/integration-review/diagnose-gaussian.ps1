$ErrorActionPreference='Stop'
$out=$PSScriptRoot
$proc=Get-Process -Name gaussian_tests -ErrorAction SilentlyContinue | Select-Object -First 1
$record=[ordered]@{timestamp=(Get-Date -Format o);note='Read-only diagnostic snapshot; no process/environment changes';process=$null}
if($proc) {
  $record.process=[ordered]@{pid=$proc.Id;cpu_seconds=$proc.CPU;working_set_bytes=$proc.WorkingSet64;started=$proc.StartTime.ToString('o');threads=$proc.Threads.Count}
  $record.modules=@($proc.Modules | Where-Object {$_.ModuleName -match 'torch|c10|cudnn|cublas|nvrtc|nvcuda|iomp|libomp'} | ForEach-Object {
    [ordered]@{name=$_.ModuleName;path=$_.FileName;product_version=$_.FileVersionInfo.ProductVersion}
  })
}
$record.gpu_query=@(& nvidia-smi --query-gpu=name,driver_version,pstate,utilization.gpu,utilization.memory,memory.used,memory.free --format=csv)
$record.launch_script=Get-Content C:\Users\User\Work\mink-lab\results\round10\integration-final\ctest-cuda.ps1
$record.environment_script_thread_settings=@(Select-String -Path C:\Users\User\Work\mink-lab\tools\mink-env.ps1 -Pattern 'OMP|MKL|THREAD' | ForEach-Object {$_.Line})
$record.selected_diagnostic_shell_environment=[ordered]@{OMP_NUM_THREADS=$env:OMP_NUM_THREADS;MKL_NUM_THREADS=$env:MKL_NUM_THREADS;OMP_DYNAMIC=$env:OMP_DYNAMIC;CUDA_MODULE_LOADING=$env:CUDA_MODULE_LOADING;CUBLAS_WORKSPACE_CONFIG=$env:CUBLAS_WORKSPACE_CONFIG}
$record.environment_limit='Selected variables are this diagnostic shell, not a direct read of the already running process environment. Launcher and mink-env scripts were inspected.'
$record.dll_file_ids=@()
foreach($name in @('torch_cpu.dll','torch_cuda.dll')) {
  $record.dll_file_ids += [ordered]@{name=$name;loaded_path_id=(& fsutil file queryfileid "C:\Users\User\Work\mink-build\integration-cuda\$name") -join ' ';installed_path_id=(& fsutil file queryfileid "C:\Users\User\Work\mink-env\libtorch-2.15.0-cu134\libtorch\lib\$name") -join ' '}
}
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$out\gaussian-diagnostic.json"
$record.process
$record.gpu_query
$record.dll_file_ids
