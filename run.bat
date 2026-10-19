@echo off
REM Jalankan transcriber tanpa perlu aktivasi venv (bisa dari CMD maupun PowerShell).
REM Contoh:  .\run.bat --file antrian\bab_thaharah.txt
REM          .\run.bat check        (cek GPU)
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo .venv belum ada. Jalankan dulu: .\setup_windows.bat
    exit /b 1
)
if /i "%~1"=="check" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0check_gpu.py"
    exit /b %errorlevel%
)
"%~dp0.venv\Scripts\python.exe" "%~dp0run.py" %*
exit /b %errorlevel%
