# Windows 10/11 x64. Run as the student, without administrator privileges.
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'GeoExcel-Map'),
    [string]$SourceArchive,
    [string]$PythonExe,
    [string]$DesktopDir = [Environment]::GetFolderPath('DesktopDirectory')
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo el comando: $Executable $($Arguments -join ' ') (codigo $LASTEXITCODE). Vuelve a ejecutar el instalador para reintentar."
    }
}

function Test-Python {
    param([string]$Executable)
    if (-not $Executable -or -not (Test-Path -LiteralPath $Executable)) { return $false }
    & $Executable -c 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) else 1)' 2>$null
    return $LASTEXITCODE -eq 0
}

if (-not [Environment]::Is64BitOperatingSystem) { throw 'Se requiere Windows de 64 bits.' }
if (-not (Test-Path -LiteralPath $DesktopDir -PathType Container)) { throw "No se encontro el escritorio: $DesktopDir" }
$InstallDir = [IO.Path]::GetFullPath($InstallDir)
$marker = Join-Path $InstallDir '.geoexcel-install'
if ((Test-Path -LiteralPath $InstallDir) -and -not (Test-Path -LiteralPath $marker)) {
    throw "La carpeta $InstallDir ya existe y no fue creada por este instalador. Elige otra carpeta con -InstallDir."
}
$running = Get-CimInstance Win32_Process -Filter "name = 'python.exe'" | Where-Object {
    $_.ExecutablePath -and $_.ExecutablePath.StartsWith($InstallDir + '\', [StringComparison]::OrdinalIgnoreCase)
}
if ($running) { throw 'Cierra GeoExcel Map antes de instalar o actualizar.' }

$temp = Join-Path ([IO.Path]::GetTempPath()) ('geoexcel-install-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    Write-Host '[1/4] Descargando GeoExcel Map...'
    $archive = Join-Path $temp 'geoexcel.zip'
    if ($SourceArchive) {
        Copy-Item -LiteralPath $SourceArchive -Destination $archive
    } else {
        Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/federicobalm/geoexcel-map/archive/refs/heads/main.zip' -OutFile $archive
    }
    $unpack = Join-Path $temp 'source'
    Expand-Archive -LiteralPath $archive -DestinationPath $unpack
    $source = @(Get-ChildItem -LiteralPath $unpack -Directory)
    if ($source.Count -ne 1 -or -not (Test-Path -LiteralPath (Join-Path $source[0].FullName 'launcher.py'))) {
        throw 'El archivo descargado no contiene una version valida de GeoExcel Map.'
    }
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Set-Content -LiteralPath $marker -Value 'GeoExcel Map managed installation' -Encoding ASCII

    Write-Host '[2/4] Preparando Python...'
    $runtime = Join-Path $InstallDir 'runtime\python.exe'
    if ($PythonExe) {
        if (-not (Test-Python $PythonExe)) { throw 'Python debe ser una version entre 3.11 y 3.13.' }
    } elseif (Test-Python $runtime) {
        $PythonExe = $runtime
    } else {
        $py = Get-Command py -ErrorAction SilentlyContinue
        if ($py) {
            $candidate = & $py.Source -3 -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and (Test-Python $candidate)) { $PythonExe = $candidate }
        }
        if (-not $PythonExe) {
            $installer = Join-Path $temp 'python-installer.exe'
            Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $installer
            $signature = Get-AuthenticodeSignature -FilePath $installer
            if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
                throw 'No se pudo verificar la firma del instalador oficial de Python.'
            }
            $runtimeDir = Join-Path $InstallDir 'runtime'
            $process = Start-Process -FilePath $installer -ArgumentList @('/quiet', 'InstallAllUsers=0', "TargetDir=`"$runtimeDir`"", 'PrependPath=0', 'Include_launcher=0', 'Include_test=0', 'Include_doc=0', 'Shortcuts=0') -Wait -PassThru
            if ($process.ExitCode -notin @(0, 3010)) { throw "La instalacion de Python fallo ($($process.ExitCode))." }
            $PythonExe = $runtime
            if (-not (Test-Python $PythonExe)) { throw 'Python no quedo disponible. Reintenta la instalacion.' }
        }
    }

    Write-Host '[3/4] Instalando la aplicacion y el exportador PDF...'
    # Copy only application files. Existing classroom data and .env are preserved.
    foreach ($name in @('app', 'sample_data', 'static', 'scripts', 'app.py', 'launcher.py', 'iniciar_geoexcel_map.bat', 'requirements.txt', 'README.md', 'LICENSE')) {
        Copy-Item -LiteralPath (Join-Path $source[0].FullName $name) -Destination $InstallDir -Recurse -Force
    }
    $venvDir = Join-Path $InstallDir '.venv'
    $venvPython = Join-Path $venvDir 'Scripts\python.exe'
    $complete = Join-Path $venvDir '.setup_complete'
    if (Test-Path -LiteralPath $complete) { Remove-Item -LiteralPath $complete }
    if (-not (Test-Path -LiteralPath $venvPython)) {
        Invoke-Checked $PythonExe @('-m', 'venv', $venvDir)
    }
    Invoke-Checked $venvPython @('-m', 'pip', 'install', '-r', (Join-Path $InstallDir 'requirements.txt'))
    Invoke-Checked $venvPython @('-m', 'playwright', 'install', 'chromium')
    Set-Content -LiteralPath $complete -Value '' -Encoding ASCII

    Write-Host '[4/4] Creando el acceso directo en el escritorio...'
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut((Join-Path $DesktopDir 'GeoExcel Map.lnk'))
    $shortcut.TargetPath = Join-Path $InstallDir 'iniciar_geoexcel_map.bat'
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.IconLocation = (Join-Path $InstallDir 'static\resources\app_icon\icon.ico') + ',0'
    $shortcut.Description = 'GeoExcel Map - mapas y analisis Rossmo'
    $shortcut.Save()
    Write-Host "Listo. Abre 'GeoExcel Map' desde el escritorio. Instalado en: $InstallDir" -ForegroundColor Green
} finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force }
}
