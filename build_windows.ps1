# KooDynaErrorAnalyzer Windows EXE 빌드 (PowerShell)
# 실행법: powershell -ExecutionPolicy Bypass -File .\build_windows.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "============================================"
Write-Host "  KooDynaErrorAnalyzer Windows EXE 빌드"
Write-Host "============================================"
Write-Host ""

# 가상환경 확인
$PipExe   = Join-Path $ScriptDir "venv\Scripts\pip.exe"
$PyiExe   = Join-Path $ScriptDir "venv\Scripts\pyinstaller.exe"
$EntryPy  = Join-Path $ScriptDir "src\koodyna\__main__.py"

if (-not (Test-Path (Join-Path $ScriptDir "venv\Scripts\python.exe"))) {
    Write-Error "가상환경이 없습니다. install.bat을 먼저 실행하세요."
    exit 1
}

# [1/2] PyInstaller 설치
Write-Host "[1/2] PyInstaller 설치 중..."
& $PipExe install pyinstaller
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller 설치 실패 (exit code $LASTEXITCODE)"
    exit 1
}
Write-Host ""

# [2/2] 빌드
Write-Host "[2/2] 빌드 중..."
Write-Host ""

$env:PYTHONPATH = Join-Path $ScriptDir "src"

$HiddenImports = @(
    "koodyna", "koodyna.parsers", "koodyna.parsers.d3hsp",
    "koodyna.parsers.glstat", "koodyna.parsers.status",
    "koodyna.parsers.profile", "koodyna.parsers.messag",
    "koodyna.analysis", "koodyna.analysis.energy",
    "koodyna.analysis.timestep", "koodyna.analysis.warnings",
    "koodyna.analysis.contact", "koodyna.analysis.performance",
    "koodyna.analysis.diagnostics",
    "koodyna.report", "koodyna.report.terminal",
    "koodyna.report.json_report", "koodyna.report.html_report",
    "koodyna.knowledge", "koodyna.knowledge.warning_db",
    "tkinter", "tkinter.filedialog", "tkinter.scrolledtext",
    "webbrowser"
)

$Args = @("--onefile", "--log-level", "DEBUG", "--name", "koodyna")
foreach ($mod in $HiddenImports) {
    $Args += "--hidden-import=$mod"
}
$Args += @("--paths=src", $EntryPy)

& $PyiExe @Args
$BuildExit = $LASTEXITCODE

Write-Host ""
if ($BuildExit -ne 0) {
    Write-Host "============================================"
    Write-Host "  빌드 실패 (exit code $BuildExit)"
    Write-Host "============================================"
    exit 1
}

$ExePath = Join-Path $ScriptDir "dist\koodyna.exe"
if (Test-Path $ExePath) {
    Write-Host "============================================"
    Write-Host "  빌드 성공: dist\koodyna.exe"
    Write-Host "============================================"
    Write-Host ""
    Write-Host "이 파일만 복사하면 Python 없이 실행 가능합니다."
    Write-Host ""
    Write-Host "사용법:"
    Write-Host "  dist\koodyna.exe [결과폴더경로]"
    Write-Host "  dist\koodyna.exe D:\결과폴더\ --html report.html"
} else {
    Write-Host "============================================"
    Write-Host "  빌드 실패: dist\koodyna.exe 생성되지 않음"
    Write-Host "============================================"
    exit 1
}
