@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" -X utf8 main.py
if errorlevel 1 pause
exit /b
:missing
echo Execute INSTALAR.cmd primeiro.
pause
exit /b 1
