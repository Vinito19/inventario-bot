@echo off
chcp 65001 >nul
title Bot Inventario VCH

echo.
echo ==========================================
echo  Iniciando Bot de Inventario VCH
echo ==========================================
echo.

cd /d "%~dp0"

:: Verificar que existe el entorno virtual
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] No se encuentra venv\Scripts\python.exe
    echo Ejecuta primero: python -m venv venv && venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Verificar .env
if not exist ".env" (
    echo [ERROR] No se encuentra archivo .env
    pause
    exit /b 1
)

echo [OK] Entorno listo. Iniciando bot...
echo.

venv\Scripts\python.exe -X utf8 bot.py

echo.
echo Bot detenido.
pause