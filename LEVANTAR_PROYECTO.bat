@echo off
chcp 65001 >nul
echo ===========================================================================
echo   PULSEGUARD CLOUD - REACTIVAR / DESPLEGAR PROYECTO EN AWS
echo ===========================================================================
echo.
echo Asegurate de haber pegado tus credenciales nuevas del dia de hoy en:
echo   aws_credentials.txt
echo.
cd /d "%~dp0"
"C:\Users\Yahir\.local\bin\uv.exe" run --with boto3 --with requests python infra/deploy.py
echo.
echo ===========================================================================
echo   LISTO PARA GRABAR TU VIDEO. COPIA LA URL DEL LOAD BALANCER DE ARRIBA.
echo ===========================================================================
pause
