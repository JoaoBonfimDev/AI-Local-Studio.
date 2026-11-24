@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" -X utf8 scripts\test_local_whisper.py
set "studio_ia_exit=%errorlevel%"
pause
exit /b %studio_ia_exit%
:missing
echo Execute INSTALAR.cmd e INSTALAR_IA.cmd primeiro.
pause
exit /b 1
