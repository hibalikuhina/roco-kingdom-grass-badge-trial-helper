<#
.SYNOPSIS
    Start Icon Matcher.

.DESCRIPTION
    Prepares the virtualenv if it is missing (or if its packages are), then
    starts the GUI.  Run with no arguments for everyday use: no console window,
    databases in .\data, and the app detached so this shell stays free.

.PARAMETER Root
    Folder holding the db_XXX directories.  Default: .\data next to this script.
    Use it to keep separate collections, e.g. -Root D:\icons\roco.

.PARAMETER Console
    Start with python.exe instead of pythonw.exe, so a console window stays
    open and any error is visible.  Use this when something misbehaves.

.PARAMETER Log
    Write the app's output to this file (and errors to <Log>.err).  Useful for
    reporting a crash without watching the console.

.PARAMETER Wait
    Block until the app is closed and return its exit code, instead of
    returning as soon as it starts.

.PARAMETER Reinstall
    Delete the virtualenv and build it again from requirements.txt.

.PARAMETER SkipChecks
    Skip the venv and dependency checks and launch straight away (a second or
    two faster once you know the install is fine).

.EXAMPLE
    .\run.ps1
    Normal start.

.EXAMPLE
    .\run.ps1 -Root D:\icons\roco
    Start on a different collection of databases.

.EXAMPLE
    .\run.ps1 -Console -Log .\iconmatcher.log
    Start with a visible console and keep the output for later.

.EXAMPLE
    .\run.ps1 -Reinstall
    Rebuild the virtualenv, then start.
#>
[CmdletBinding()]
param(
    [string]$Root,
    [switch]$Console,
    [string]$Log,
    [switch]$Wait,
    [switch]$Reinstall,
    [switch]$SkipChecks
)

$ErrorActionPreference = 'Stop'

$here = $PSScriptRoot
$venv = Join-Path $here '.venv'
$py = Join-Path $venv 'Scripts\python.exe'
$pyw = Join-Path $venv 'Scripts\pythonw.exe'
$requirements = Join-Path $here 'requirements.txt'


function Install-Venv {
    Write-Host "Creating virtualenv in $venv ..."
    $interpreter = Get-Command python -ErrorAction SilentlyContinue
    $launcherArgs = @()
    if (-not $interpreter) {
        $interpreter = Get-Command py -ErrorAction SilentlyContinue
        $launcherArgs = @('-3')
    }
    if (-not $interpreter) {
        throw "No Python 3 found on PATH. Install Python 3.10+ (python.org) and run this again."
    }
    & $interpreter.Source @launcherArgs -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create the virtualenv (exit $LASTEXITCODE)." }
    Install-Requirements
}

function Install-Requirements {
    Write-Host "Installing numpy + pillow ..."
    & $py -m pip install --quiet --upgrade pip
    & $py -m pip install --quiet -r $requirements
    if ($LASTEXITCODE -ne 0) { throw "Installing requirements failed (exit $LASTEXITCODE)." }
}


if ($Reinstall -and (Test-Path $venv)) {
    Write-Host "Removing $venv ..."
    Remove-Item -Recurse -Force $venv
}

if (-not $SkipChecks) {
    if (-not (Test-Path $py)) {
        Install-Venv
    }
    else {
        # cheap probe that always exits 0, so a missing package is not an error
        $probe = & $py -c "import importlib.util as u; print('ok' if u.find_spec('numpy') and u.find_spec('PIL') else 'missing')"
        if ($probe -ne 'ok') { Install-Requirements }
    }
}

if (-not (Test-Path $py)) {
    throw "No virtualenv at $venv. Run this script without -SkipChecks to build it."
}

$exe = $pyw
if ($Console) { $exe = $py }
if (-not (Test-Path $exe)) { $exe = $py }

$appArgs = @((Join-Path $here 'main.py'))
if ($Root) {
    $resolved = $Root
    if (-not [System.IO.Path]::IsPathRooted($resolved)) {
        $resolved = Join-Path (Get-Location).Path $Root
    }
    if (-not (Test-Path $resolved)) { New-Item -ItemType Directory -Force $resolved | Out-Null }
    $appArgs += @('--root', $resolved)
}

$start = @{
    FilePath         = $exe
    ArgumentList     = $appArgs
    WorkingDirectory = $here
    PassThru         = $true
}
if ($Wait) { $start.Wait = $true }
if ($Log) {
    $start.RedirectStandardOutput = $Log
    $start.RedirectStandardError = "$Log.err"
    $start.NoNewWindow = $true
}

$proc = Start-Process @start

if ($Wait) {
    exit $proc.ExitCode
}

$where = if ($Root) { $appArgs[-1] } else { Join-Path $here 'data' }
Write-Host "Icon Matcher started (PID $($proc.Id)).  Databases: $where"
if ($Log) { Write-Host "Output: $Log  (errors: $Log.err)" }
