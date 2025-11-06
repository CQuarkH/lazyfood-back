@echo off
echo ====================================
echo Deteniendo contenedores...
echo ====================================
docker-compose down

echo.
echo ====================================
echo Reconstruyendo con nuevas dependencias...
echo ====================================
docker-compose build --no-cache

echo.
echo ====================================
echo Iniciando contenedores...
echo ====================================
docker-compose up

pause
