@echo off
setlocal
title GeoExcel Map v3

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto :setup

set "PYTHON_CMD="
where py >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py"

if not defined PYTHON_CMD (
    where python >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo.
    echo ERROR: No se encontro Python en el sistema.
    echo Instala Python 3.11 o superior y vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Creando entorno virtual...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :fail
)

:setup
if not exist ".venv\.setup_complete" (
    echo.
    echo Instalando dependencias iniciales...
    call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :fail

    echo.
    echo Instalando Chromium para exportacion PDF...
    call ".venv\Scripts\python.exe" -m playwright install chromium
    if errorlevel 1 goto :fail

    type nul > ".venv\.setup_complete"
)

echo.
echo Iniciando GeoExcel Map v3. El navegador se abrira cuando este listo.
call ".venv\Scripts\python.exe" launcher.py
set "LAUNCH_EXIT=%errorlevel%"
if not "%LAUNCH_EXIT%"=="0" pause
exit /b %LAUNCH_EXIT%

:fail
echo.
echo La preparacion automatica fallo.
echo Revisa el mensaje anterior y vuelve a intentarlo.
echo.
pause
exit /b 1
