param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('phase3', 'phase4')]
    [string]$Track,
    [string]$Study = '',
    [string]$Baseline = '',
    [int]$Limit = 0
)
$ErrorActionPreference = 'Stop'
$workRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (!$Study) {
    $studyName = if ($Track -eq 'phase3') { 'phase03_matched_benchmark_v1' } else { 'phase04_matched_benchmark_v1' }
    $Study = Join-Path $workRoot ("runs\" + $studyName)
}
if (!$Baseline) { $Baseline = Join-Path $workRoot 'runs\phase01_frozen_baseline_v1' }
$Study = [IO.Path]::GetFullPath($Study)
$Baseline = [IO.Path]::GetFullPath($Baseline)
if ((Split-Path $Study -Parent) -ne (Join-Path $workRoot 'runs')) {
    throw 'Study must be a direct child of btp_work/runs'
}
if ($Limit -lt 0) { throw 'Limit must be nonnegative' }
$python = Join-Path $workRoot '.venv\Scripts\python.exe'
$previousWorkRoot = [Environment]::GetEnvironmentVariable('BTP_WORK_ROOT', 'Process')
try {
    $env:BTP_WORK_ROOT = $workRoot
    if (!(Test-Path -LiteralPath (Join-Path $Study 'manifest.json'))) {
        & $python -B -X utf8 (Join-Path $PSScriptRoot 'model_comparison.py') prepare --track $Track --study $Study --baseline $Baseline
        if ($LASTEXITCODE -ne 0) { throw 'Comparison preparation failed' }
    }
    $frozenController = Join-Path $Study 'frozen\tools\model_comparison.py'
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss_ffff'
    $outLog = Join-Path $Study "controller_$stamp.stdout.txt"
    $errLog = Join-Path $Study "controller_$stamp.stderr.txt"
    $inputLog = Join-Path $Study 'controller.stdin.txt'
    if (!(Test-Path -LiteralPath $inputLog)) { [IO.File]::WriteAllText($inputLog, '') }
    $arguments = @('-B', '-X', 'utf8', ('"' + $frozenController + '"'), 'run',
        '--track', $Track, '--study', ('"' + $Study + '"'), '--baseline', ('"' + $Baseline + '"'),
        '--limit', "$Limit")
    $process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $workRoot -WindowStyle Hidden -RedirectStandardInput $inputLog -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
    Write-Output "Launcher PID: $($process.Id). Status: $Study\progress.json"
    Write-Output "Results: $Study\results.csv"
    Write-Output "Logs: $outLog ; $errLog"
}
finally {
    [Environment]::SetEnvironmentVariable('BTP_WORK_ROOT', $previousWorkRoot, 'Process')
}
