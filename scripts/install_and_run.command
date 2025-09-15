#!/bin/bash
# Este script abre una nueva ventana de Terminal y ejecuta el script de instalación principal.
# Esto es útil para los usuarios de macOS que prefieren hacer doble clic.

# Obtiene el directorio donde reside este script
DIR_OF_THIS_SCRIPT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Abre una nueva instancia de Terminal y ejecuta el script .sh
# Esto asegura que el usuario pueda ver el progreso y los mensajes de la instalación.
osascript <<EOD
tell application "Terminal"
    do script "cd '$DIR_OF_THIS_SCRIPT' && ./install_and_run.sh"
    activate
end tell
EOD