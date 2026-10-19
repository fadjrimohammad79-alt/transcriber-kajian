@echo off
setlocal
REM ============================================================
REM  Setup transcriber di Windows (GPU NVIDIA atau tanpa GPU)
REM  Jalankan sekali dari folder repo ini:  .\setup_windows.bat
REM ============================================================
cd /d "%~dp0"

echo [0/4] Mencari Python 3.10-3.12 ...
set "PY="
for %%V in (3.12 3.11 3.10) do (
    if not defined PY (
        py -%%V -c "import sys" >nul 2>&1 && set "PY=py -%%V"
    )
)
if not defined PY (
    python -c "import sys; assert (3,10) <= sys.version_info[:2] <= (3,12) and sys.maxsize > 2**32" >nul 2>&1 && set "PY=python"
)
if not defined PY (
    for %%P in ("%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%ProgramFiles%\Python312\python.exe" "%ProgramFiles%\Python311\python.exe") do (
        if not defined PY if exist %%P set PY="%%~P"
    )
)
if not defined PY goto :nopython
%PY% -c "import sys; print('      Python', sys.version.split()[0], sys.executable)"

echo [1/4] Membuat virtual environment .venv ...
REM -- cek venv rusak (mulai)
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -c "import sys" >nul 2>&1 || (
        echo      .venv tidak bisa dijalankan - dibuat di PC lain? Dibuat ulang ...
        rmdir /s /q .venv
    )
)
REM -- cek venv rusak (selesai)
if not exist .venv\Scripts\python.exe (
    %PY% -m venv .venv || goto :error
)

echo [2/4] Install library (beberapa menit, ~1.5 GB untuk library CUDA) ...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error

echo [3/4] Membuat .env ...
if not exist .env copy .env.example .env >nul

echo [4/4] Cek GPU ...
.venv\Scripts\python.exe check_gpu.py
echo.
echo Selesai. Untuk memakai (CMD atau PowerShell), dari folder ini:
echo    .\run.bat --file antrian\niat.txt
exit /b 0

:nopython
echo.
echo Python 3.10-3.12 (64-bit) belum terpasang.
echo Pasang dengan salah satu cara:
echo    winget install -e --id Python.Python.3.12
echo    atau unduh dari python.org (centang "Add python.exe to PATH")
echo Lalu TUTUP dan BUKA LAGI terminal, dan jalankan .\setup_windows.bat lagi.
exit /b 1

:error
echo.
echo GAGAL di langkah di atas. Kirim tampilan error ini untuk dibantu.
exit /b 1
