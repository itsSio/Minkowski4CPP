<#
Configure (only when needed) and build a Minkowski4CPP checkout inside the shared build lock.

  pwsh -File C:\Users\User\Work\mink-lab\tools\mink-build.ps1 -Src C:\Users\User\Work\mink-wt\<branch> `
       -Build C:\Users\User\Work\mink-build\<branch>-cuda [-Cpu] [-Targets adaptive_tests,gaussian_tests] `
       [-Config Release] [-Arch 75] [-Jobs 4] [-NoCache] [-Reconfigure] [-CMakeArgs '-DFOO=ON'] [-Who name]

- CUDA (default): CUDA 13.4.3 + LibTorch 2.15.0+cu134, sm_75. -Cpu: LibTorch 2.15.0+cpu, CPU_ONLY=ON.
  If a -Cpu checkout lacks PR #5 (fix/cpu-only-build), tools\cpu-only-fix.cmake is injected via
  CMAKE_PROJECT_INCLUDE (no source edits).
- Reconfigures only if the build dir has no build.ninja or the configure arguments changed
  (stamp: <Build>\.mink-configure-args). Ninja itself re-runs CMake when CMakeLists change.
- sccache (MSVC + nvcc) is on unless -NoCache. LibTorch DLLs are hard-linked into <Build>
  (MINK_COPY_TORCH_DLLS=OFF) instead of copying ~4 GB per build dir.
- Every build is appended to mink-lab\results\build-times.csv.
Exit code = configure or build exit code.
#>
param(
    [Parameter(Mandatory)][string]$Src,
    [Parameter(Mandatory)][string]$Build,
    [switch]$Cpu,
    [string[]]$Targets,
    [ValidateSet('Release', 'RelWithDebInfo', 'Debug', 'MinSizeRel')][string]$Config = 'Release',
    [string]$Arch = '75',
    [int]$Jobs = 4,
    [switch]$NoCache,
    [switch]$Reconfigure,
    [string[]]$CMakeArgs = @(),
    [string]$Who = $(if ($env:MINK_AGENT) { $env:MINK_AGENT } else { 'mink-build' })
)
$ErrorActionPreference = 'Stop'
$tools = $PSScriptRoot
$lab = Split-Path $tools -Parent

. (Join-Path $tools 'mink-env.ps1') -Cpu:$Cpu -Quiet

$Src = (Resolve-Path -LiteralPath $Src).Path
$Build = [IO.Path]::GetFullPath($Build)
New-Item -ItemType Directory -Force $Build | Out-Null
$torch = $env:MINK_LIBTORCH
if (-not (Test-Path (Join-Path $torch 'share\cmake\Torch\TorchConfig.cmake'))) { throw "LibTorch missing: $torch" }

# ---- configure arguments -------------------------------------------------------------------
$fwd = { param($p) $p.Replace('\', '/') }
$cfg = @(
    '-G', 'Ninja',
    "-DCMAKE_BUILD_TYPE=$Config",
    "-DCMAKE_PREFIX_PATH=$(& $fwd $torch)",
    '-DMINK_COPY_TORCH_DLLS=OFF',
    "-DMINK_USE_CCACHE=$(if ($NoCache) { 'OFF' } else { 'ON' })"
)
if ($Cpu) {
    $cfg += '-DCPU_ONLY=ON'
    $hasFix = Select-String -Path (Join-Path $Src 'CMakeLists.txt') -Pattern 'MINK_DUAL_BACKEND_SOURCES' -Quiet
    if (-not $hasFix) {
        Write-Host 'mink-build: checkout lacks PR #5 (fix/cpu-only-build); injecting tools\cpu-only-fix.cmake'
        $cfg += "-DCMAKE_PROJECT_INCLUDE=$(& $fwd (Join-Path $tools 'cpu-only-fix.cmake'))"
    }
} else {
    $cuda = & $fwd $env:MINK_CUDA_ROOT
    $cfg += @(
        '-DCPU_ONLY=OFF',
        "-DCUDAToolkit_ROOT=$cuda",
        "-DCMAKE_CUDA_COMPILER=$cuda/bin/nvcc.exe",
        "-DCMAKE_CUDA_ARCHITECTURES=$Arch",
        "-DTORCH_CUDA_ARCH_LIST=$($Arch.Substring(0, $Arch.Length - 1)).$($Arch.Substring($Arch.Length - 1))"
    )
    $env:TORCH_CUDA_ARCH_LIST = ($cfg[-1] -split '=')[1]
}
$cfg += $CMakeArgs

$stamp = Join-Path $Build '.mink-configure-args'
$want = (@("src=$Src") + $cfg) -join "`n"
$have = if (Test-Path $stamp) { Get-Content -Raw $stamp } else { '' }
$needConfigure = $Reconfigure -or -not (Test-Path (Join-Path $Build 'build.ninja')) -or ($have.Trim() -ne $want.Trim())

$t0 = Get-Date
$cfgSec = 0
if ($needConfigure) {
    if ($have -and ($have.Trim() -ne $want.Trim())) {
        # Changed generator-level args (e.g. CPU_ONLY, compilers) cannot be applied to an existing cache.
        Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $Build 'CMakeCache.txt')
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Build 'CMakeFiles')
    }
    Write-Host "mink-build: configuring $Build"
    & cmake.exe -S $Src -B $Build @cfg
    if ($LASTEXITCODE -ne 0) { Write-Host "mink-build: configure FAILED ($LASTEXITCODE)"; exit $LASTEXITCODE }
    Set-Content -NoNewline -Path $stamp -Value $want
    $cfgSec = [int]((Get-Date) - $t0).TotalSeconds
} else {
    Write-Host 'mink-build: configure args unchanged; skipping configure'
}

# ---- runtime DLLs: hard links (same volume) instead of copies -----------------------------------
foreach ($dll in Get-ChildItem (Join-Path $torch 'lib') -Filter *.dll) {
    $dst = Join-Path $Build $dll.Name
    if (-not (Test-Path $dst)) {
        try { New-Item -ItemType HardLink -Path $dst -Target $dll.FullName | Out-Null }
        catch { Copy-Item $dll.FullName $dst }
    }
}

# ---- build inside the build lock ----------------------------------------------------------------
# Under `pwsh -File`, "-Targets a,b" arrives as the single string 'a,b'; accept commas/spaces either way.
$Targets = @($Targets | ForEach-Object { $_ -split '[,\s]+' } | Where-Object { $_ })
$tgt = if ($Targets) { ' --target ' + ($Targets -join ' ') } else { '' }
$cmd = "cmake --build `"$Build`" --parallel $Jobs$tgt"
Write-Host "mink-build: $cmd"
$b0 = Get-Date
& pwsh -NoProfile -File (Join-Path $tools 'with-lock.ps1') -Kind build -Who $Who -Command $cmd
$rc = $LASTEXITCODE
$buildSec = [int]((Get-Date) - $b0).TotalSeconds

$csv = Join-Path $lab 'results\build-times.csv'
New-Item -ItemType Directory -Force (Split-Path $csv) | Out-Null
if (-not (Test-Path $csv)) { 'time,who,kind,src,build,targets,configured_s,build_s_incl_lock_wait,exit' | Set-Content $csv }
$commit = (& git -C $Src rev-parse --short HEAD 2>$null)
('{0:s},{1},{2},{3}@{4},{5},{6},{7},{8},{9}' -f (Get-Date), $Who, $env:MINK_ENV_KIND, $Src, $commit, $Build,
    ($Targets -join ' '), $cfgSec, $buildSec, $rc) | Add-Content $csv
Write-Host "mink-build: exit $rc (configure ${cfgSec}s, build ${buildSec}s incl. lock wait)"
exit $rc
