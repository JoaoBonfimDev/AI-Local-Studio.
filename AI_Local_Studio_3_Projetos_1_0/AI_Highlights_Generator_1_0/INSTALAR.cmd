@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python -m venv .venv
) else (
  py -3 -m venv .venv
)
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo Instale FFmpeg e FFprobe conforme INSTALACAO_WINDOWS.md.
  pause
  exit /b 1
)
where ffprobe >nul 2>nul
if errorlevel 1 goto :error
echo Instalacao concluida. Abra INICIAR.cmd.
pause
exit /b 0
:error
echo Nao foi possivel concluir. Leia INSTALACAO_WINDOWS.md.
pause
exit /b 1
