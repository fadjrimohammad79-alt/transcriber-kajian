@echo off
REM Jalankan transcriber tanpa perlu aktivasi venv (bisa dari CMD maupun PowerShell).
REM Contoh:  .\run.bat --file antrian\bab_thaharah.txt
REM          .\run.bat check        (cek GPU)
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo .venv belum ada. Jalankan dulu: .\setup_windows.bat
    exit /b 1
)
REM goto (bukan blok if): %errorlevel% di dalam blok ( ) sudah diganti nilainya sebelum python jalan,
REM sehingga exit code check_gpu.py selalu terbaca 0.
if /i "%~1"=="check" goto :check
"%~dp0.venv\Scripts\python.exe" "%~dp0run.py" %*
exit /b %errorlevel%

:check
"%~dp0.venv\Scripts\python.exe" "%~dp0check_gpu.py"
exit /b %errorlevel%
