param(
    [string]$UvVersion = '0.9.5',
    [string]$PythonVersion = '3.13.2'
)

# Run from any directory. Every downloaded/generated file stays under btp_work.
# Installs dependencies and records candidates; does not run upstream benchmarks.
$ErrorActionPreference = 'Stop'
$workRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$toolRoot = Join-Path $workRoot '.compiler-tools'
$envRoot = Join-Path $workRoot '.venv'
$attemptId = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
$recordRoot = Join-Path $workRoot "runs\phase_00\setup_$attemptId"
New-Item -ItemType Directory -Path $recordRoot -Force | Out-Null
New-Item -ItemType Directory -Path $toolRoot -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $toolRoot 'tmp') -Force | Out-Null
$env:TEMP = Join-Path $toolRoot 'tmp'
$env:TMP = $env:TEMP
$env:UV_CACHE_DIR = Join-Path $toolRoot 'uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $toolRoot 'python'
$env:UV_PYTHON_BIN_DIR = Join-Path $toolRoot 'bin'
$env:UV_PYTHON_INSTALL_REGISTRY = '0'
$env:UV_PYTHON_INSTALL_BIN = '0'
$env:UV_NO_MODIFY_PATH = '1'
$env:UV_NO_CONFIG = '1'
$env:PIP_CACHE_DIR = Join-Path $toolRoot 'pip-cache'
$env:MPLCONFIGDIR = Join-Path $toolRoot 'matplotlib'
$env:XDG_CACHE_HOME = Join-Path $toolRoot 'xdg-cache'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:NUMEXPR_NUM_THREADS = '1'
$env:VECLIB_MAXIMUM_THREADS = '1'
$env:PYTHONHASHSEED = '0'
$state = [ordered]@{
    status = 'in_progress'; uv_version = $UvVersion; requested_python = $PythonVersion
    venv = $envRoot; compiler_smoke_passed = $false
    lock_status = 'not_validated_by_compiler_smokes'; error = $null
}

function Invoke-UvChecked {
    param([string[]]$UvArgs)
    & $script:uvExe @UvArgs
    if ($LASTEXITCODE -ne 0) { throw "uv failed (exit $LASTEXITCODE): $UvArgs" }
}

try {
    $uvRoot = Join-Path $toolRoot "uv-$UvVersion"
    $script:uvExe = Join-Path $uvRoot 'uv.exe'
    if (-not (Test-Path -LiteralPath $script:uvExe)) {
        if (Test-Path -LiteralPath $uvRoot) { throw "Incomplete uv directory exists: $uvRoot" }
        $zipPath = Join-Path $toolRoot "uv-$UvVersion-x86_64-pc-windows-msvc.zip"
        $url = "https://github.com/astral-sh/uv/releases/download/$UvVersion/uv-x86_64-pc-windows-msvc.zip"
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $zipPath -TimeoutSec 30
        $state.uv_archive_sha256 = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLower()
        Expand-Archive -LiteralPath $zipPath -DestinationPath $uvRoot
        if (-not (Test-Path -LiteralPath $script:uvExe)) { throw 'uv.exe missing from extracted archive' }
    }
    $state.uv_exe_sha256 = (Get-FileHash -LiteralPath $script:uvExe -Algorithm SHA256).Hash.ToLower()
    Invoke-UvChecked -UvArgs @('--version')
    $auditPython = Join-Path $workRoot '.research-tools\python\python.exe'
    $rftRoot = Join-Path $workRoot 'vendor\NAQC_Compiler-3d1f09233c2acd357fd9fbfad1b5300a921d301a'
    $dasRoot = Join-Path $workRoot 'vendor\DasAtom-73a6bdf0fd200b2733745211eaf2e0c1e17f496a'
    if (-not (Test-Path -LiteralPath (Join-Path $rftRoot 'requirements.txt')) -or
        -not (Test-Path -LiteralPath (Join-Path $dasRoot 'requirements.txt'))) {
        & $auditPython -X utf8 (Join-Path $PSScriptRoot 'recover_phase00_sources.py') --fetch --output "runs/phase_00/setup_$attemptId/source_recovery.json"
        if ($LASTEXITCODE -ne 0) { throw 'Pinned-source recovery failed; see source_recovery.json' }
    }
    # Recheck any recovered AGENTS.md before the first compiler execution.
    $state.source_agents_files = @(Get-ChildItem -LiteralPath $rftRoot,$dasRoot -Filter AGENTS.md -Recurse -File | ForEach-Object FullName)
    if (Test-Path -LiteralPath $envRoot) { throw "Refusing to replace an existing environment: $envRoot" }
    Invoke-UvChecked -UvArgs @('venv','--managed-python','--python',$PythonVersion,$envRoot)
    $venvPython = Join-Path $envRoot 'Scripts\python.exe'
    Invoke-UvChecked -UvArgs @('pip','install','--python',$venvPython,
        '-r',(Join-Path $rftRoot 'requirements.txt'),'-r',(Join-Path $dasRoot 'requirements.txt'),'pip')
    Invoke-UvChecked -UvArgs @('pip','check','--python',$venvPython)
    & $venvPython -c 'import qiskit,numpy,scipy,networkx,rustworkx,pandas,matplotlib,plotly,openpyxl; import sys; print(sys.version)'
    if ($LASTEXITCODE -ne 0) { throw 'Required compiler import probe failed' }
    $freeze = & $script:uvExe pip freeze --python $venvPython
    if ($LASTEXITCODE -ne 0) { throw 'Dependency freeze failed' }
    [IO.File]::WriteAllLines((Join-Path $recordRoot 'requirements.candidate.txt'),$freeze)
    Invoke-UvChecked -UvArgs @('--quiet','pip','compile','--python',$venvPython,
        (Join-Path $recordRoot 'requirements.candidate.txt'),'--generate-hashes',
        '--output-file',(Join-Path $recordRoot 'requirements.candidate.lock'))
    $state.status = 'installed_import_checked_compiler_smokes_pending'
    Write-Output "Environment installed: $venvPython"
    Write-Output 'Dependency lock is a candidate until both compiler smoke cases pass.'
} catch {
    $state.status = 'error'
    $state.error = $_.Exception.Message
    Write-Output $state.error
} finally {
    $state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $recordRoot 'setup_status.json') -Encoding utf8
    Write-Output "Setup record: $recordRoot"
}
if ($state.status -eq 'error') { exit 2 }
