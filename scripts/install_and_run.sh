#!/bin/bash
set -e

# --- INSTALADOR ROBUSTO PARA LINUX/MACOS ---

echo_step() { echo; echo "-----> $1"; echo; }
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

# --- 1. INSTALACIÓN DE DEPENDENCIAS DEL SISTEMA ---
echo_step "Paso 1: Asegurando dependencias del sistema..."
INSTALL_CMD=""
PACKAGES_TO_INSTALL=""
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v apt-get &> /dev/null; then
        INSTALL_CMD="sudo apt-get update && sudo apt-get install -y"
        PACKAGES_TO_INSTALL="git python3 python3-pip python3-venv"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew &> /dev/null; then
        if ask_yes_no "Homebrew no está instalado. ¿Instalarlo ahora?"; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        else echo "Instalación cancelada."; exit 1; fi
    fi
    INSTALL_CMD="brew install"
    PACKAGES_TO_INSTALL="git python"
fi
if [ -n "$INSTALL_CMD" ]; then
    echo "Se instalarán/actualizarán los siguientes paquetes: $PACKAGES_TO_INSTALL"
    if ask_yes_no "¿Deseas continuar?"; then
        eval "$INSTALL_CMD $PACKAGES_TO_INSTALL"
    else echo "Instalación cancelada."; exit 1; fi
else
    echo "No se pudo detectar un gestor de paquetes (apt o brew)."; exit 1;
fi
echo "Todas las dependencias del sistema están presentes."

# --- 2. DESCARGA Y CONFIGURACIÓN DEL PROYECTO ---
PROJECT_DIR="geoexcel-map"
REPO_URL="https://github.com/federicobalm/geoexcel-map.git"
echo_step "Paso 2: Descargando el proyecto desde GitHub..."
if [ -d "$PROJECT_DIR" ]; then
    if ask_yes_no "La carpeta '$PROJECT_DIR' ya existe. ¿Eliminar y continuar?"; then
        rm -rf "$PROJECT_DIR"
    else echo "Instalación cancelada."; exit 1; fi
fi
git clone --depth 1 "$REPO_URL" "$PROJECT_DIR"
cd "$PROJECT_DIR"
echo "Proyecto descargado en la carpeta '$PROJECT_DIR'."

# --- 3. CONFIGURACIÓN DEL ENTORNO DE PYTHON ---
echo_step "Paso 3: Configurando el entorno de Python..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip > /dev/null
pip install -r requirements.txt
if [ ! -f "data/user.json" ]; then
    echo; echo "Por favor, introduce tus datos para firmar las exportaciones."
    read -p " > Nombre: " user_name < /dev/tty
    read -p " > Apellido: " user_surname < /dev/tty
    read -p " > Email: " user_email < /dev/tty
    mkdir -p data
    cat <<EOF > data/user.json
{ "nombre": "$user_name", "apellido": "$user_surname", "email": "$user_email" }
EOF
fi
cat <<EOF > run.sh
#!/bin/bash
cd "\$(dirname "\$0")"
echo "Iniciando GeoExcel Map..."
source .venv/bin/activate
python3 app.py
EOF
chmod +x run.sh

# --- 4. FINALIZACIÓN ---
# --- CAMBIO CLAVE: Detectar y mostrar la IP local ---
LOCAL_IP=$(hostname -I | awk '{print $1}')
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="127.0.0.1"
fi

echo; echo "========================================================="
echo "  INSTALACION FINALIZADA"
echo "========================================================="
echo; echo "Para iniciar la aplicacion en el futuro, ve a la carpeta:"
echo "  $PWD"
echo "Y ejecuta el comando:"
echo "  ./run.sh"
echo
echo "La aplicacion se iniciara ahora."
echo "Puedes acceder a ella desde otro dispositivo en la misma red en la direccion:"
echo "  http://$LOCAL_IP:5000"
echo
read -p "Presiona Enter para iniciar el servidor..." < /dev/tty
python3 app.py