<#
.SYNOPSIS
    启动“洛克王国 草系徽章之旅 助手”。
    Start the Roco Kingdom Grass Badge Trail Helper.

.DESCRIPTION
    如果虚拟环境不存在（或者缺了依赖包），会先自动装好，然后启动图形界面。
    平时直接运行、不带任何参数就行：没有黑框控制台，图鉴存在 .\data 里，
    程序在后台运行，不占用当前这个终端。

    Prepares the virtualenv if it is missing (or if its packages are), then
    starts the GUI.  Run with no arguments for everyday use: no console window,
    databases in .\data, and the app detached so this shell stays free.

.PARAMETER Root
    存放 db_XXX 图鉴文件夹的目录，默认是脚本旁边的 .\data。
    想分开管理不同的收藏时用它，例如 -Root D:\icons\roco。

    Folder holding the db_XXX directories.  Default: .\data next to this script.
    Use it to keep separate collections, e.g. -Root D:\icons\roco.

.PARAMETER Lang
    界面语言：zh（简体中文，默认）或 en（English）。不写就沿用上次的选择，
    程序里的“语言 / Language”菜单随时也能切换。

    Interface language: zh (Simplified Chinese, the default) or en.  Omit it to
    keep whatever you chose last time; the Language menu switches it any time.

.PARAMETER Console
    用 python.exe 而不是 pythonw.exe 启动，保留一个控制台窗口，方便看到报错。
    出问题的时候用这个。

    Start with python.exe instead of pythonw.exe, so a console window stays
    open and any error is visible.  Use this when something misbehaves.

.PARAMETER Log
    把程序输出写到这个文件（错误写到 <Log>.err）。想反馈崩溃又不想一直盯着
    控制台时很有用。

    Write the app's output to this file (and errors to <Log>.err).  Useful for
    reporting a crash without watching the console.

.PARAMETER Wait
    等程序关闭后再返回，并带回它的退出码，而不是启动完就返回。

    Block until the app is closed and return its exit code, instead of
    returning as soon as it starts.

.PARAMETER Reinstall
    删掉虚拟环境，按 requirements.txt 重新装一遍。

    Delete the virtualenv and build it again from requirements.txt.

.PARAMETER SkipChecks
    跳过虚拟环境和依赖检查，直接启动（确认装好之后能快一两秒）。

    Skip the venv and dependency checks and launch straight away (a second or
    two faster once you know the install is fine).

.EXAMPLE
    .\run.ps1
    正常启动。 / Normal start.

.EXAMPLE
    .\run.ps1 -Lang en
    以英文界面启动。 / Start with the English interface.

.EXAMPLE
    .\run.ps1 -Root D:\icons\roco
    使用另一组图鉴。 / Start on a different collection of databases.

.EXAMPLE
    .\run.ps1 -Console -Log .\iconmatcher.log
    带控制台启动，并把输出留档。
    Start with a visible console and keep the output for later.

.EXAMPLE
    .\run.ps1 -Reinstall
    重建虚拟环境后启动。 / Rebuild the virtualenv, then start.
#>
[CmdletBinding()]
param(
    [string]$Root,
    [ValidateSet('zh', 'en')]
    [string]$Lang,
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
    Write-Host "正在创建虚拟环境 $venv ...  /  Creating virtualenv in $venv ..."
    $interpreter = Get-Command python -ErrorAction SilentlyContinue
    $launcherArgs = @()
    if (-not $interpreter) {
        $interpreter = Get-Command py -ErrorAction SilentlyContinue
        $launcherArgs = @('-3')
    }
    if (-not $interpreter) {
        throw "PATH 上找不到 Python 3，请先安装 Python 3.10+（python.org）再运行。  /  " +
              "No Python 3 found on PATH. Install Python 3.10+ (python.org) and run this again."
    }
    & $interpreter.Source @launcherArgs -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        throw "创建虚拟环境失败（退出码 $LASTEXITCODE）。  /  " +
              "Could not create the virtualenv (exit $LASTEXITCODE)."
    }
    Install-Requirements
}

function Install-Requirements {
    Write-Host "正在安装 numpy + pillow ...  /  Installing numpy + pillow ..."
    & $py -m pip install --quiet --upgrade pip
    & $py -m pip install --quiet -r $requirements
    if ($LASTEXITCODE -ne 0) {
        throw "安装依赖失败（退出码 $LASTEXITCODE）。  /  " +
              "Installing requirements failed (exit $LASTEXITCODE)."
    }
}


if ($Reinstall -and (Test-Path $venv)) {
    Write-Host "正在删除 $venv ...  /  Removing $venv ..."
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
    throw "$venv 里没有虚拟环境，请去掉 -SkipChecks 再运行一次以创建它。  /  " +
          "No virtualenv at $venv. Run this script without -SkipChecks to build it."
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
if ($Lang) { $appArgs += @('--lang', $Lang) }

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

$where = if ($Root) { $resolved } else { Join-Path $here 'data' }
Write-Host "助手已启动（PID $($proc.Id)），图鉴目录：$where"
Write-Host "Helper started (PID $($proc.Id)).  Databases: $where"
if ($Log) {
    Write-Host "输出：$Log （错误：$Log.err）  /  Output: $Log  (errors: $Log.err)"
}
