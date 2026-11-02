<#
Minkowski4CPP native Windows build environment (no admin, no Docker).
Dot-source it in pwsh:
    . C:\Users\User\Work\mink-lab\tools\mink-env.ps1          # CUDA 13.4 + LibTorch 2.15.0+cu134
    . C:\Users\User\Work\mink-lab\tools\mink-env.ps1 -Cpu     # LibTorch 2.15.0+cpu (CUDA not on PATH)
Sets: MSVC (vcvars64) vars, cmake 4.2.3 + ninja + sccache + nvcc on PATH, CUDA_PATH/CUDA_HOME/
CUDAToolkit_ROOT/CUDACXX, TORCH_CUDA_ARCH_LIST=7.5, MINK_LIBTORCH (selected LibTorch root),
MINK_CUDA_ROOT, MINK_ENV_KIND (cuda|cpu). Idempotent; -Force re-imports vcvars.
#>
param([switch]$Cpu, [switch]$Force, [switch]$Quiet)

$MinkEnvRoot = 'C:\Users\User\Work\mink-env'
$vsRoot = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools'
$vcvars = Join-Path $vsRoot 'VC\Auxiliary\Build\vcvars64.bat'

# 1. MSVC: run vcvars64 in cmd and import the resulting environment (once per process).
if ($Force -or -not $env:MINK_VCVARS_IMPORTED) {
    if (-not (Test-Path -LiteralPath $vcvars)) { throw "vcvars64.bat not found: $vcvars" }
    $dump = & cmd.exe /d /s /c "`"$vcvars`" >nul 2>&1 && set"
    if ($LASTEXITCODE -ne 0) { throw "vcvars64.bat failed (exit $LASTEXITCODE)" }
    foreach ($line in $dump) {
        if ($line -match '^([^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
        }
    }
    $env:MINK_VCVARS_IMPORTED = '1'
}

# 2. Tool paths (prepended; earlier entries win). Strip any previous mink-env entries first so
#    switching -Cpu <-> CUDA in one shell does not leave the other toolkit on PATH.
$cudaRoot = Join-Path $MinkEnvRoot 'cuda-13.4'
$torchCuda = Join-Path $MinkEnvRoot 'libtorch-2.15.0-cu134\libtorch'
$torchCpu = Join-Path $MinkEnvRoot 'libtorch-2.15.0-cpu\libtorch'
$pre = @(
    (Join-Path $MinkEnvRoot 'cmake-4.2.3\bin'),
    (Join-Path $MinkEnvRoot 'sccache-0.19.0\sccache-v0.19.0-x86_64-pc-windows-msvc'),
    (Join-Path $vsRoot 'Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja')
)
if ($Cpu) {
    $torch = $torchCpu
} else {
    $torch = $torchCuda
    $pre += @(
        (Join-Path $cudaRoot 'bin'),
        (Join-Path $cudaRoot 'bin\x64'),
        (Join-Path $cudaRoot 'libnvvm\bin'),
        (Join-Path $cudaRoot 'nsight_compute'),
        (Join-Path $cudaRoot 'nsight_systems\target-windows-x64')
    )
}
$pre += (Join-Path $torch 'lib')
$kept = ($env:PATH -split ';') | Where-Object { $_ -and ($_ -notlike "$MinkEnvRoot*") }
$env:PATH = (($pre | Where-Object { Test-Path -LiteralPath $_ }) + $kept) -join ';'

# 3. CUDA / Torch variables. Forward slashes avoid CMake escape errors in Torch's config.
if ($Cpu) {
    foreach ($v in 'CUDA_PATH', 'CUDA_HOME', 'CUDAToolkit_ROOT', 'CUDACXX', 'TORCH_CUDA_ARCH_LIST') {
        Remove-Item "env:$v" -ErrorAction SilentlyContinue
    }
    $env:MINK_ENV_KIND = 'cpu'
} else {
    $c = $cudaRoot.Replace('\', '/')
    $env:CUDA_PATH = $c
    $env:CUDA_HOME = $c
    $env:CUDAToolkit_ROOT = $c
    $env:CUDACXX = "$c/bin/nvcc.exe"
    $env:TORCH_CUDA_ARCH_LIST = '7.5'
    $env:MINK_ENV_KIND = 'cuda'
}
$env:MINK_CUDA_ROOT = $cudaRoot
$env:MINK_LIBTORCH = $torch
$env:MINK_ENV_ROOT = $MinkEnvRoot

# 4. sccache: one shared local cache for all agents (MSVC + nvcc).
$env:SCCACHE_DIR = Join-Path $MinkEnvRoot 'sccache-cache'
$env:SCCACHE_CACHE_SIZE = '30G'
$env:SCCACHE_IDLE_TIMEOUT = '0'

if (-not $Quiet) {
    $nv = if (-not $Cpu -and (Get-Command nvcc.exe -ErrorAction SilentlyContinue)) {
        ((& nvcc.exe --version) -join ' ') -replace '.*(release [0-9.]+, V[0-9.]+).*', '$1'
    } else { 'n/a' }
    Write-Host ("mink-env [{0}] MSVC {1} | {2} | nvcc {3} | torch {4}" -f $env:MINK_ENV_KIND,
        $env:VCToolsVersion, ((& cmake.exe --version | Select-Object -First 1)), $nv, $torch)
}
