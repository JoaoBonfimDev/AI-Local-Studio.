@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" -X utf8 -m unittest discover -s tests -v
set "studio_test_exit=%errorlevel%"
echo.
echo Os testes criam apenas midias sinteticas temporarias em .local\tests.
pause
exit /b %studio_test_exit%
:missing
echo Execute INSTALAR.cmd primeiro.
pause
exit /b 1
