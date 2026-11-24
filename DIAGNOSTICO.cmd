@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" -X utf8 main.py --doctor
pause
exit /b
:missing
echo Execute INSTALAR.cmd primeiro.
pause
exit /b 1
