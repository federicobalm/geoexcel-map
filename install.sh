#!/bin/bash
set -e

# --- INSTALADOR PROFESIONAL PARA LINUX Y MACOS ---

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_step() { printf "\n${GREEN}-----> $1${NC}\n\n"; }
echo_info() { printf "${YELLOW}$1${NC}\n"; }
echo_error() { printf "\n${RED}ERROR: $1${NC}\n\n"; }
ask_yes_no() {
    while true; do
        read -p "$1 [y/n]: " yn < /dev/tty
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            * ) echo "Por favor, responde 'y' (sí) o 'n' (no).";;
        esac
    done
}

echo -e "${GREEN}========================================================="
echo -e "        Instalador de GeoExcel Map para Linux/macOS"
echo -e "=========================================================${NC}"

# --- 1. VERIFICACIÓN DE DEPENDENCIAS ---
echo_step "Paso 1: Verificando dependencias del sistema..."

check_command() {
    if ! command -v $1 &> /dev/null; then
        echo_error "El comando '$1' no se encuentra. Es una dependencia obligatoria."
        echo_info "Por favor, instala el paquete '$2' usando el gestor de paquetes de tu sistema (ej: sudo apt install $2) y vuelve a ejecutar este script."
        exit 1
    fi
    echo -e "  [✓] $1 encontrado."
}

check_command "python3" "python3"
check_command "pip3" "python3-pip"
check_command "git" "git"
if ! python3 -c "import venv" &> /dev/null; then
    echo_error "El módulo 'venv' de Python no se encuentra."
    echo_info "Por favor, instala el paquete 'python3-venv' (ej: sudo apt install python3-venv) y vuelve a ejecutar este script."
    exit 1
fi
echo -e "${GREEN}Todas las dependencias están presentes.${NC}"

# --- 2. CONFIGURACIÓN DEL PROYECTO ---
echo_step "Paso 2: Configurando el entorno de Python..."

echo "Creando entorno virtual en .venv..."
python3 -m venv .venv

echo "Instalando dependencias (esto puede tardar varios minutos)..."
source .venv/bin/activate
pip install --upgrade pip > /dev/null
pip install -r requirements.txt
deactivate
echo -e "${GREEN}Dependencias instaladas correctamente.${NC}"

# --- 3. CONFIGURACIÓN DE USUARIO Y ACCESOS DIRECTOS ---
echo_step "Paso 3: Finalizando la configuración..."

if [ ! -f "data/user.json" ]; then
    echo
    echo_info "Por favor, introduce tus datos para firmar las exportaciones."
    read -p " > Nombre: " user_name < /dev/tty
    read -p " > Apellido: " user_surname < /dev/tty
    read -p " > Email: " user_email < /dev/tty
    mkdir -p data
    cat <<EOF > data/user.json
{ "nombre": "$user_name", "apellido": "$user_surname", "email": "$user_email" }
EOF
fi

echo "Creando script de arranque rápido 'run.sh'..."
cat <<EOF > run.sh
#!/bin/bash
cd "\$(dirname "\$0")"
echo "Iniciando GeoExcel Map..."
source .venv/bin/activate
python3 app.py
EOF
chmod +x run.sh

# Crear alias
if ask_yes_no "¿Deseas crear un comando 'geoexcel' para iniciar la aplicación desde cualquier lugar de la terminal?"; then
    ALIAS_CMD="alias geoexcel='cd \"$PWD\" && ./run.sh'"
    SHELL_CONFIG=""
    if [ -f "$HOME/.zshrc" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    fi

    if [ -n "$SHELL_CONFIG" ]; then
        if ! grep -q "alias geoexcel" "$SHELL_CONFIG"; then
            echo -e "\n# Alias para GeoExcel Map\n$ALIAS_CMD" >> "$SHELL_CONFIG"
            echo_info "Alias 'geoexcel' añadido a $SHELL_CONFIG."
            echo_info "Abre una nueva terminal para usarlo."
        else
            echo_info "El alias 'geoexcel' ya existe."
        fi
    else
        echo_info "No se pudo encontrar el archivo .bashrc o .zshrc para añadir el alias."
    fi
fi

echo -e "\n${GREEN}========================================================="
echo -e "                INSTALACION FINALIZADA"
echo -e "=========================================================${NC}"
echo
echo -e "${YELLOW}Para iniciar la aplicación, ejecuta el comando:${NC}"
echo -e "  ./run.sh"
echo
echo -e "${YELLOW}O, si creaste el alias, abre una nueva terminal y escribe:${NC}"
echo -e "  geoexcel"
echo