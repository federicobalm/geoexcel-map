@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: --- INSTALADOR PROFESIONAL PARA WINDOWS ---

:: Habilitar colores en la consola
for /F "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do (
  set "DEL=%%a"
)
call :colorEcho 0a "========================================================="
call :colorEcho 0a "        Instalador de GeoExcel Map para Windows"
call :colorEcho 0a "========================================================="
echo.

:: --- 1. VERIFICACIÓN DE DEPENDENCIAS ---
call :colorEcho 0e "Paso 1: Verificando dependencias del sistema..."

:CHECK_PYTHON
echo Verificando la instalacion de Python...
py -3 --version >nul 2>&1
if !errorlevel! NEQ 0 (
    call :colorEcho 0c "ERROR: Python 3 no se encuentra."
    echo.
    echo Por favor, descarga e instala Python desde:
    call :colorEcho 0b "https://www.python.org/downloads/"
    echo.
    call :colorEcho 0c "IMPORTANTE: Durante la instalacion, asegurate de marcar la casilla 'Add Python to PATH'."
    echo.
    pause
    exit /b 1
)
call :colorEcho 0a "Python encontrado."

:CHECK_GIT
echo Verificando la instalacion de Git...
git --version >nul 2>&1
if !errorlevel! NEQ 0 (
    call :colorEcho 0c "ERROR: Git no se encuentra."
    echo.
    echo Por favor, descarga e instala Git desde:
    call :colorEcho 0b "https://git-scm.com/download/win"
    echo.
    pause
    exit /b 1
)
call :colorEcho 0a "Git encontrado."
echo.

:: --- 2. CONFIGURACIÓN DEL PROYECTO ---
call :colorEcho 0e "Paso 2: Configurando el entorno de Python..."

echo Creando entorno virtual en .venv...
py -3 -m venv .venv

echo Instalando dependencias (esto puede tardar varios minutos)...
call .\.venv\Scripts\python.exe -m pip install --upgrade pip > nul
call .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if !errorlevel! NEQ 0 (
    call :colorEcho 0c "ERROR: Fallo la instalacion de las dependencias. Revisa tu conexion a internet."
    pause
    exit /b 1
)
call :colorEcho 0a "Dependencias instaladas correctamente."
echo.

:: --- 3. CONFIGURACIÓN DE USUARIO Y ACCESOS DIRECTOS ---
call :colorEcho 0e "Paso 3: Finalizando la configuracion..."

if not exist data ( mkdir data )
if not exist data\user.json (
    echo.
    echo Por favor, introduce tus datos para firmar las exportaciones.
    set /p user_name=" > Nombre: "
    set /p user_surname=" > Apellido: "
    set /p user_email=" > Email: "
    (echo { "nombre": "!user_name!", "apellido": "!user_surname!", "email": "!user_email!" }) > data\user.json
)

echo Creando script de arranque rapido 'run.bat'...
(
    echo @echo off
    echo cd /d "%%~dp0"
    echo echo Iniciando GeoExcel Map...
    echo .\.venv\Scripts\python.exe app.py
    echo pause
) > run.bat

echo Creando Acceso Directo en el Escritorio...
set SCRIPT_PATH=%CD%\run.bat
set ICON_PATH=%CD%\static\resources\app_icon\icon.ico
set SHORTCUT_NAME="GeoExcel Map.lnk"
set POWERSHELL_COMMAND="$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.Environment]::GetFolderPath('Desktop') + '\' + '%SHORTCUT_NAME%'); $s.TargetPath = '%SCRIPT_PATH%'; $s.IconLocation = '%ICON_PATH%'; $s.Save()"
powershell -Command "!POWERSHELL_COMMAND!" >nul

call :colorEcho 0a "========================================================="
call :colorEcho 0a "                INSTALACION FINALIZADA"
call :colorEcho 0a "========================================================="
echo.
call :colorEcho 0b "Se ha creado un acceso directo en tu Escritorio."
echo.
echo Para iniciar la aplicacion, puedes usar el acceso directo
echo o hacer doble clic en el archivo 'run.bat' dentro de esta carpeta.
echo.
pause
exit /b 0

:: Función para imprimir con colores
:colorEcho
echo %DEL%
echo %DEL% %2
exit /b