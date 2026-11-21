@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute INSTALAR.cmd primeiro.
  pause
  exit /b 1
)
set RUN_MEDIA_TESTS=1
set RUN_GPU_TESTS=1
set RUN_HTTP_TESTS=1
".venv\Scripts\python.exe" -m unittest discover -s tests -v
pause
