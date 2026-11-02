param(
    [string]$Study = '',
    [int]$Limit = 0
)
$ErrorActionPreference = 'Stop'
$workRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (!$Study) { $Study = Join-Path $workRoot 'runs\phase01_frozen_baseline_v1' }
$Study = [IO.Path]::GetFullPath($Study)
if ((Split-Path (Split-Path $Study -Parent) -Parent) -ne $workRoot -or (Split-Path (Split-Path $Study -Parent) -Leaf) -ne 'runs') {
    throw 'Study must be a direct child of btp_work/runs'
}
$python = Join-Path $workRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath (Join-Path $Study 'manifest.json'))) {
    & $python -B -X utf8 (Join-Path $PSScriptRoot 'standalone_baseline.py') prepare --study $Study
    if ($LASTEXITCODE -ne 0) { throw 'Baseline preparation failed' }
}
$frozenController = Join-Path $Study 'frozen\tools\standalone_baseline.py'
$repairManifest = Join-Path $Study 'controller_repair_v1\manifest.json'
if (Test-Path -LiteralPath $repairManifest) {
    $frozenController = Join-Path $Study 'controller_repair_v1\tools\standalone_baseline.py'
    Write-Output 'Using verified controller repair; it waits for an existing controller to finish.'
}
$launchStamp = Get-Date -Format 'yyyyMMdd_HHmmss_ffff'
$outLog = Join-Path $Study "controller_$launchStamp.stdout.txt"
$errLog = Join-Path $Study "controller_$launchStamp.stderr.txt"
# Windows Start-Process creates an independent process. Logs and checkpoints
# outlive this shell; no console window or active agent is required.
$arguments = @('-B', '-X', 'utf8', ('"' + $frozenController + '"'), 'run', '--study', ('"' + $Study + '"'), '--limit', "$Limit")
$process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $workRoot -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
Write-Output "Launcher PID: $($process.Id). Controller status: $Study\progress.json"
Write-Output "Logs: $outLog ; $errLog"
