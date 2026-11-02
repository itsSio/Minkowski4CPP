<#
Serialize shared resources between parallel agents.
  -Kind gpu   : exclusive GPU (all GPU tests/benchmarks/profiling) - 1 holder
  -Kind build : compile slot (cmake --build) - 2 holders max (16 GB RAM, 6 cores)
Usage:
  pwsh -File with-lock.ps1 -Kind gpu -Command "build\adaptive_bench.exe --json out.json"
Exit code = the wrapped command's exit code. Waits are logged to locks.log.
#>
param(
    [Parameter(Mandatory)][ValidateSet('gpu','build','bench')][string]$Kind,
    [Parameter(Mandatory)][string]$Command,
    [string]$Who = $env:MINK_AGENT
)
# bench = exclusive machine for timing: GPU + both build slots. Builds -> GPU order everywhere (a bench only holds
# slots while taking the GPU with a timeout) -> no deadlock.
function Take([System.Threading.Mutex]$m) { try { [void]$m.WaitOne() } catch [System.Threading.AbandonedMutexException] {} }
$gpu = [System.Threading.Mutex]::new($false, 'Local\mink-gpu-0')
$builds = @('Local\mink-build-0','Local\mink-build-1') | ForEach-Object { [System.Threading.Mutex]::new($false, $_) }
$log = Join-Path $PSScriptRoot '..\locks.log'
$t0 = Get-Date
# FIFO: mutex waits are not fair, so build and bench waiters queue by ticket and only the oldest live ticket
# waits on the build slots. Tickets of dead processes (or reused PIDs) are dropped.
# MINK_QUEUED_SINCE (local time, e.g. 2026-11-01T11:39:00) keeps a requeued waiter's original place.
# A bench needs both slots; while it has waited < $BenchGrace, build tickets behind it may still take a slot that is
# free right now (non-blocking), so a waiting bench does not idle a slot. After that the bench has strict priority.
$BenchGrace = [TimeSpan]::FromMinutes(10)
function NewTicket {
    $qdir = Join-Path $PSScriptRoot '..\locks\build-queue'
    New-Item -ItemType Directory -Force $qdir | Out-Null
    $since = [DateTime]::UtcNow
    if ($env:MINK_QUEUED_SINCE) { $since = ([DateTime]::Parse($env:MINK_QUEUED_SINCE)).ToUniversalTime() }
    $ticket = Join-Path $qdir ('{0:D19}-{1}.ticket' -f $since.Ticks, $PID)
    # Lines: who, our process start time (PID-reuse guard), kind, real enqueue time.
    Set-Content $ticket @($Who, (Get-Process -Id $PID).StartTime.ToUniversalTime().Ticks, $Kind, [DateTime]::UtcNow.Ticks)
    return $ticket
}
function LiveTickets {
    $qdir = Join-Path $PSScriptRoot '..\locks\build-queue'
    Get-ChildItem $qdir -Filter *.ticket | Sort-Object Name | ForEach-Object {
        $p = [int]($_.BaseName -split '-')[1]
        $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
        $lines = @(Get-Content $_.FullName -ErrorAction SilentlyContinue)
        if ($proc -and ($lines.Count -lt 2 -or $proc.StartTime.ToUniversalTime().Ticks -eq [int64]$lines[1])) {
            [pscustomobject]@{ Path = $_.FullName; Kind = $(if ($lines.Count -ge 3) { $lines[2] } else { 'build' });
                Enq = $(if ($lines.Count -ge 4) { [DateTime]::new([int64]$lines[3], 'Utc') } else { [DateTime]::UtcNow }) }
        } else { Remove-Item $_.FullName -ErrorAction SilentlyContinue }
    }
}
# 'head' when ours is the oldest live ticket; 'try' when only grace-period benches are ahead; else 'wait'.
function Turn($ticket) {
    $mine = (Get-Item $ticket).FullName
    $ahead = $false
    foreach ($t in LiveTickets) {
        if ($t.Path -eq $mine) { return $(if ($ahead) { 'try' } else { 'head' }) }
        # A bench that is waiting for the GPU (kind 'benchgpu') holds no slot: builds behind it may take a free one.
        if ($Kind -ne 'build') { return 'wait' }
        if ($t.Kind -ne 'benchgpu' -and ($t.Kind -ne 'bench' -or ([DateTime]::UtcNow - $t.Enq) -ge $BenchGrace)) { return 'wait' }
        $ahead = $true
    }
    return 'head'
}
function TakeWithin([System.Threading.Mutex]$m, [int]$ms) {
    try { return $m.WaitOne($ms) } catch [System.Threading.AbandonedMutexException] { return $true }
}
function GpuFree { if (TakeWithin $gpu 0) { $gpu.ReleaseMutex(); return $true }; return $false }
function SetTicketKind($ticket, $k) {
    $lines = @(Get-Content $ticket); $lines[2] = $k; Set-Content $ticket $lines
}
function TryAny([int]$ms) {
    try { return [System.Threading.WaitHandle]::WaitAny([System.Threading.WaitHandle[]]$builds, $ms) }
    catch [System.Threading.AbandonedMutexException] { return $_.Exception.MutexIndex }
}
switch ($Kind) {
    'gpu'   { Take $gpu; $held = @($gpu); $idx = 0 }
    'bench' {
        # Build slots first (via the queue), GPU last, so a waiting bench never idles the GPU.
        # Order builds -> gpu everywhere: gpu holders never wait on builds, so no deadlock.
        # A bench at the head of the queue first waits for the GPU WITHOUT holding build slots (ticket kind
        # 'benchgpu' lets builds behind it run meanwhile), then takes both slots, then the GPU with a timeout; if a
        # GPU job got in between, it releases the slots and waits again. Only one bench is at the head at a time.
        $ticket = NewTicket
        try {
            while ($true) {
                while ((Turn $ticket) -ne 'head') { Start-Sleep -Seconds 2 }
                if (-not (GpuFree)) {
                    SetTicketKind $ticket 'benchgpu'
                    while (-not (GpuFree)) { Start-Sleep -Seconds 5 }
                    SetTicketKind $ticket 'bench'
                    continue  # re-check the queue: builds may have started meanwhile
                }
                Take $builds[0]; Take $builds[1]
                if (TakeWithin $gpu 60000) { break }
                $builds[1].ReleaseMutex(); $builds[0].ReleaseMutex()
            }
        } finally { Remove-Item $ticket -ErrorAction SilentlyContinue }
        $held = @($gpu) + $builds; $idx = 0
    }
    'build' {
        $ticket = NewTicket
        try {
            while ($true) {
                $turn = Turn $ticket
                if ($turn -eq 'head') { $idx = TryAny -1; break }
                if ($turn -eq 'try') { $idx = TryAny 0; if ($idx -ne [System.Threading.WaitHandle]::WaitTimeout) { break } }
                Start-Sleep -Seconds 2
            }
        } finally { Remove-Item $ticket -ErrorAction SilentlyContinue }
        $held = @($builds[$idx])
    }
}
$waited = [int]((Get-Date) - $t0).TotalSeconds
Add-Content $log ("{0:s} {1} slot{2} acquired by '{3}' after {4}s: {5}" -f (Get-Date), $Kind, $idx, $Who, $waited, $Command)
try {
    & ([scriptblock]::Create($Command))
    $code = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 0 }
} finally {
    foreach ($m in $held) { $m.ReleaseMutex() }
    Add-Content $log ("{0:s} {1} slot{2} released by '{3}'" -f (Get-Date), $Kind, $idx, $Who)
}
exit $code
