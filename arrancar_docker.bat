@echo off
rem doble clic y queda la tesis andando en Docker
setlocal
cd /d "%~dp0"

set "DOCKER=docker"
where docker >nul 2>&1 || set "DOCKER=C:\Program Files\Docker\Docker\resources\bin\docker.exe"

rem abre el 8020 para entrar desde otros equipos (solo la 1a vez)
netsh advfirewall firewall show rule name="Tesis 8020" >nul 2>&1
if errorlevel 1 (
    echo Abriendo el puerto 8020 en el firewall ^(acepta el aviso de Windows^)...
    powershell -NoProfile -Command "Start-Process netsh -Verb RunAs -Wait -ArgumentList 'advfirewall firewall add rule name=\"Tesis 8020\" dir=in action=allow protocol=TCP localport=8020'"
)

rem prende Docker si esta apagado
"%DOCKER%" info >nul 2>&1
if errorlevel 1 (
    echo Abriendo Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    for /l %%i in (1,1,60) do (
        timeout /t 3 /nobreak >nul
        "%DOCKER%" info >nul 2>&1 && goto docker_listo
    )
    echo Docker no respondio en 3 minutos. Abre Docker Desktop a mano y vuelve a intentar.
    pause
    exit /b 1
)
:docker_listo

rem levanta la tesis, abierta a la red
set "DOCKER_IP=0.0.0.0"
echo Levantando la tesis...
"%DOCKER%" compose up --build -d
if errorlevel 1 (
    echo Fallo docker compose. Revisa los mensajes de arriba.
    pause
    exit /b 1
)

rem espera a que la pagina responda
echo Esperando a que la pagina responda...
for /l %%i in (1,1,40) do (
    powershell -NoProfile -Command "try { Invoke-WebRequest http://localhost:8020/health -UseBasicParsing -TimeoutSec 3 | Out-Null; exit 0 } catch { exit 1 }" && goto app_lista
    timeout /t 3 /nobreak >nul
)
echo La pagina aun no responde. Revisa: docker compose logs app
pause
exit /b 1
:app_lista

echo.
echo ==========================================================
echo  Tesis lista
echo   En este PC:          http://localhost:8020
for /f "usebackq delims=" %%a in (`powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'vEthernet|Loopback' -and $_.IPAddress -notlike '169.254*' }).IPAddress"`) do echo   Desde otro equipo:   http://%%a:8020
echo.
echo  Queda corriendo aunque cierres esta ventana.
echo  Para apagarla:  docker compose down
echo ==========================================================
start http://localhost:8020
pause
