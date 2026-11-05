#!/usr/bin/env bash
# Separate Unix installer. The Windows installer is intentionally independent.
set -euo pipefail

main() {
    if [[ "${1:-}" == "--help" ]]; then
        printf '%s\n' 'GeoExcel Map: instalador Linux/macOS.' \
            'Ejecutar como usuario normal, sin sudo.' \
            'GEOEXCEL_INSTALL_DIR permite elegir la carpeta de instalacion.'
        return
    fi
    if [[ "$(id -u)" == 0 ]]; then
        printf '%s\n' 'Ejecuta este instalador como tu usuario, sin sudo.' >&2
        return 1
    fi
    local system root temp uv python
    system="$(uname -s)"
    case "$system" in
        Linux) root="${GEOEXCEL_INSTALL_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/geoexcel-map}" ;;
        Darwin) root="${GEOEXCEL_INSTALL_DIR:-$HOME/Library/Application Support/GeoExcel-Map}" ;;
        *) printf '%s\n' 'Este instalador solo admite Linux y macOS.' >&2; return 1 ;;
    esac
    case "$(uname -m)" in
        x86_64|aarch64|arm64) ;;
        *) printf '%s\n' 'Se requiere arquitectura x86_64 o ARM64.' >&2; return 1 ;;
    esac
    [[ "$root" == /* ]] || { printf '%s\n' 'La carpeta de instalacion debe ser una ruta absoluta.' >&2; return 1; }
    if [[ -e "$root" && ! -f "$root/.geoexcel-unix-install" ]]; then
        printf 'La carpeta ya existe y no pertenece a este instalador: %s\n' "$root" >&2
        return 1
    fi
    command -v curl >/dev/null || { printf '%s\n' 'Instala curl para continuar.' >&2; return 1; }
    command -v tar >/dev/null || { printf '%s\n' 'Instala tar para continuar.' >&2; return 1; }
    umask 022
    mkdir -p "$root"
    printf '%s\n' 'GeoExcel Map Unix installation' > "$root/.geoexcel-unix-install"
    temp="$(mktemp -d "${TMPDIR:-/tmp}/geoexcel-install.XXXXXXXX")"
    # Expand the quoted path now; local variables are unavailable when EXIT runs.
    trap "rm -rf -- $(printf '%q' "$temp")" EXIT
    printf '%s\n' '[1/4] Preparando Python aislado...'
    uv="$root/tools/uv"
    if [[ ! -x "$uv" ]]; then
        curl --fail --show-error --silent --location --retry 3 https://astral.sh/uv/install.sh -o "$temp/uv-install.sh"
        UV_UNMANAGED_INSTALL="$root/tools" sh "$temp/uv-install.sh"
    fi
    export UV_PYTHON_INSTALL_DIR="$root/python"
    export UV_PYTHON_BIN_DIR="$root/tools"
    "$uv" python install 3.12
    python="$("$uv" python find --managed-python 3.12)"
    printf '%s\n' '[2/4] Descargando GeoExcel Map...'
    if [[ -n "${GEOEXCEL_SOURCE_ARCHIVE:-}" ]]; then
        cp "$GEOEXCEL_SOURCE_ARCHIVE" "$temp/source.tar.gz"
    else
        curl --fail --show-error --silent --location --retry 3 \
            https://github.com/federicobalm/geoexcel-map/archive/refs/heads/main.tar.gz -o "$temp/source.tar.gz"
    fi
    mkdir "$temp/source"
    "$python" -c 'import sys, tarfile; tarfile.open(sys.argv[1]).extractall(sys.argv[2], filter="data")' "$temp/source.tar.gz" "$temp/source"
    local sources=("$temp/source/"*)
    [[ ${#sources[@]} == 1 && -f "${sources[0]}/scripts/install_unix.py" ]] || {
        printf '%s\n' 'La descarga no contiene un instalador valido.' >&2; return 1;
    }
    "$python" "${sources[0]}/scripts/install_unix.py" --root "$root" --source "${sources[0]}" --uv "$uv"
}

# Keep execution last so an interrupted download piped to bash cannot run half a script.
main "$@"
