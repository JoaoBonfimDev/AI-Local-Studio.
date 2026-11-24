@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
where python >nul 2>nul
if errorlevel 1 goto launcher
python -X utf8 scripts\setup_windows.py
goto finish
:launcher
where py >nul 2>nul
if errorlevel 1 goto missing
py -3 -X utf8 scripts\setup_windows.py
:finish
if errorlevel 1 goto failure
echo.
echo Pronto. Abra INICIAR.cmd. Para transcricao, abra INSTALAR_IA.cmd.
pause
exit /b 0
:missing
echo Instale Python 3.13 ou 3.14 de python.org, incluindo o PATH e Tcl/Tk.
pause
exit /b 1
:failure
echo Nao foi possivel concluir a instalacao. Veja a mensagem acima e docs\SOLUCAO_DE_PROBLEMAS.md.
pause
exit /b 1
