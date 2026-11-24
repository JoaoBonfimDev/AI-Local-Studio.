@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" -X utf8 -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 goto failure
echo.
echo Faster-Whisper instalado. Escolha seu modelo local na interface ou use Baixar modelo.
echo O diagnostico e a primeira transcricao verificam CUDA. A CPU continua disponivel.
pause
exit /b 0
:missing
echo Execute INSTALAR.cmd primeiro.
pause
exit /b 1
:failure
echo Uma dependencia nao possui wheel compativel ou a conexao falhou.
echo O Studio continua funcionando sem transcricao. Veja docs\GPU_CUDA.md.
echo Python 3.13 pode ser usado em uma NOVA pasta de instalacao se faltarem wheels para 3.14.
pause
exit /b 1
