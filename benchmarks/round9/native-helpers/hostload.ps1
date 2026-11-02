# Append a host-contention sample (CPU % over -Sec seconds, top CPU processes, nvidia-smi) to -Log.
param([string]$Log, [string]$Tag, [int]$Sec = 20)
$c = Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples $Sec -ErrorAction SilentlyContinue
$cpu = if ($c) { [Math]::Round(($c.CounterSamples.CookedValue | Measure-Object -Average).Average, 1) } else { -1 }
$top = Get-Process | Sort-Object CPU -Descending | Select-Object -First 6 | ForEach-Object { "$($_.ProcessName)" } 
$g = (& nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader) -join ' '
"{0:s} [{1}] cpu_total_avg_{2}s={3}% gpu(util,used,total)={4} top_cpu_time={5}" -f (Get-Date), $Tag, $Sec, $cpu, $g, ($top -join ',') | Add-Content $Log
