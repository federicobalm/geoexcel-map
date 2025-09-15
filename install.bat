@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

:: --- INSTALADOR FINAL, AUTÓNOMO Y ROBUSTO PARA WINDOWS ---

echo.
echo =========================================================
echo  Instalador de GeoExcel Map para Windows
echo =========================================================
echo.

:: --- 1. VERIFICACIÓN DE DEPENDENCIAS ---
echo "Paso 1: Verificando dependencias del sistema..."

:CHECK_PYTHON
echo Verificando la instalacion de Python...
py -3 --version >nul 2>&1
if !errorlevel! NEQ 0 (
    echo. & echo ADVERTENCIA: Python 3 no se encuentra.
    set /p install_python="¿Descargar e instalar Python ahora? (s/n): "
    if /i "!install_python!"=="s" (
        powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
        echo. & echo ============================ ¡ACCIÓN REQUERIDA! ============================
        echo Se abrira el instalador de Python. Sigue estos pasos:
        echo   1. MARCA LA CASILLA "Add Python.exe to PATH".
        echo   2. Haz clic en "Install Now" y completa la instalacion.
        echo =============================================================================
        echo. & pause
        start /wait "" "%TEMP%\python_installer.exe"
        echo. & echo ============================ ¡PASO FINAL IMPORTANTE! ============================
        echo Python ha sido instalado. Por favor, CIERRA esta ventana y
        echo VUELVE A EJECUTAR el comando de instalacion en una nueva
        echo consola de Administrador para continuar.
        echo ================================================================================
        echo. & pause & exit /b 0
    ) else ( echo Instalacion cancelada. & pause & exit /b 1 )
)
echo "Python encontrado."

:CHECK_GIT
where git >nul 2>&1
if !errorlevel! NEQ 0 (
    echo. & echo ADVERTENCIA: Git no se encuentra.
    set /p install_git="¿Descargar e instalar Git ahora? (s/n): "
    if /i "!install_git!"=="s" (
        powershell -Command "Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.45.1.windows.1/Git-2.45.1-64-bit.exe' -OutFile '%TEMP%\git_installer.exe'"
        echo. & echo ============================ ¡ACCIÓN REQUERIDA! ============================
        echo Se abrira el instalador de Git. Acepta las opciones por defecto.
        echo =============================================================================
        echo. & pause
        start /wait "" "%TEMP%\git_installer.exe"
        echo. & echo ============================ ¡PASO FINAL IMPORTANTE! ============================
        echo Git ha sido instalado. Por favor, CIERRA esta ventana y
        echo VUELVE A EJECUTAR el comando de instalacion en una nueva
        echo consola de Administrador para continuar.
        echo ================================================================================
        echo. & pause & exit /b 0
    ) else ( echo Instalacion cancelada. & pause & exit /b 1 )
)
echo "Git encontrado."

:: --- 2. DESCARGA Y CONFIGURACIÓN DEL PROYECTO ---
SET PROJECT_DIR="geoexcel-map"
SET REPO_URL="https://github.com/federicobalm/geoexcel-map.git"

echo.
echo "Paso 2: Descargando el proyecto..."
if exist %PROJECT_DIR% (
    echo La carpeta '%PROJECT_DIR%' ya existe.
) else (
    git clone --depth 1 %REPO_URL% %PROJECT_DIR%
)
cd %PROJECT_DIR%

echo.
echo "Paso 3: Configurando el entorno de Python..."
echo Creando entorno virtual en .venv...
py -3 -m venv .venv

echo Instalando dependencias (esto puede tardar varios minutos)...
call .\.venv\Scripts\python.exe -m pip install --upgrade pip > nul
call .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if !errorlevel! NEQ 0 (
    echo "ERROR: Fallo la instalacion de las dependencias. Revisa tu conexion a internet."
    pause
    exit /b 1
)

if not exist data ( mkdir data )
if not exist data\user.json (
    echo. & echo Por favor, introduce tus datos para firmar las exportaciones.
    set /p user_name=" > Nombre: "
    set /p user_surname=" > Apellido: "
    set /p user_email=" > Email: "
    (echo { "nombre": "!user_name!", "apellido": "!user_surname!", "email": "!user_email!" }) > data\user.json
)

echo Creando script de arranque rapido 'run.bat'...
(
    echo @echo off
    echo cd /d "%%~dp0"
    echo .\.venv\Scripts\python.exe app.py
    echo pause
) > run.bat

echo Creando Acceso Directo en el Escritorio...
set SCRIPT_PATH=%CD%\run.bat
set ICON_PATH=%CD%\static\resources\app_icon\icon.ico
set SHORTCUT_NAME="GeoExcel Map.lnk"
set POWERSHELL_COMMAND="$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.Environment]::GetFolderPath('Desktop') + '\' + '%SHORTCUT_NAME%'); $s.TargetPath = '%SCRIPT_PATH%'; $s.IconLocation = '%ICON_PATH%'; $s.Save()"
powershell -Command "!POWERSHELL_COMMAND!" >nul

echo. & echo =========================================================
echo  INSTALACION FINALIZADA
echo =========================================================
echo. & echo Se ha creado un acceso directo en tu Escritorio.
echo. & echo La aplicacion se iniciara ahora por primera vez...
echo. & pause

call run.bat

ENDLOCAL