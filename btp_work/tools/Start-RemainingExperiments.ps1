param(
    [ValidateSet('All', 'Weighting', 'Assignment', 'Hardware', 'Workloads', 'Scale')]
    [string]$Suite = 'All',
    [string]$Study = '',
    [ValidateRange(0.01, 6.0)]
    [double]$MaxHours = 6.0,
    [switch]$Smoke
)
$ErrorActionPreference = 'Stop'
$experimentWorkRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (!$Study) { $Study = Join-Path $experimentWorkRoot 'runs\remaining_experiments_6h_v2' }
$Study = [IO.Path]::GetFullPath($Study)
if ((Split-Path $Study -Parent) -ne (Join-Path $experimentWorkRoot 'runs')) {
    throw 'Study must be a direct child of btp_work/runs'
}
$experimentPython = Join-Path $experimentWorkRoot '.venv\Scripts\python.exe'
$priorExperimentRoot = [Environment]::GetEnvironmentVariable('BTP_WORK_ROOT', 'Process')
try {
    $env:BTP_WORK_ROOT = $experimentWorkRoot
    $prepareArgs = @('-B', '-X', 'utf8', (Join-Path $PSScriptRoot 'remaining_experiments.py'),
                     'prepare', '--study', $Study, '--max-hours', "$MaxHours")
    if ($Smoke) { $prepareArgs += '--smoke' }
    & $experimentPython @prepareArgs
    if ($LASTEXITCODE -ne 0) { throw 'Frozen experiment preparation or integrity check failed' }
    $frozenController = Join-Path $Study 'frozen\tools\remaining_experiments.py'
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss_ffff'
    $outLog = Join-Path $Study "controller_$stamp.stdout.txt"
    $errLog = Join-Path $Study "controller_$stamp.stderr.txt"
    $inputLog = Join-Path $Study 'controller.stdin.txt'
    if (!(Test-Path -LiteralPath $inputLog)) { [IO.File]::WriteAllText($inputLog, '') }
    $runArgs = @('-B', '-X', 'utf8', ('"' + $frozenController + '"'), 'run', '--study',
                 ('"' + $Study + '"'), '--suite', $Suite.ToLowerInvariant())
    $process = Start-Process -FilePath $experimentPython -ArgumentList $runArgs -WorkingDirectory $experimentWorkRoot -WindowStyle Hidden -RedirectStandardInput $inputLog -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
    Write-Output "Measurement controller started. PID: $($process.Id)."
    Write-Output "Progress: $Study\progress.json"
    Write-Output "Measurements: $Study\results.csv"
    Write-Output 'No research analysis, report or presentation will run automatically.'
    Write-Output 'You may close this terminal. Keep the computer powered on; do not manually sleep or shut it down.'
}
finally {
    [Environment]::SetEnvironmentVariable('BTP_WORK_ROOT', $priorExperimentRoot, 'Process')
}
