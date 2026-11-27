@echo off
chcp 65001 >nul
echo ===========================================================================
echo   PULSEGUARD CLOUD - LIMPIAR RECURSOS AWS (DESPUES DE GRABAR TU VIDEO)
echo ===========================================================================
echo.
cd /d "%~dp0"
"C:\Users\Yahir\.local\bin\uv.exe" run --with boto3 python infra/destroy.py
echo.
pause
