"""Unix installation driver, invoked by install.sh with managed Python 3.12."""
import argparse
import fcntl
import os
from pathlib import Path
import platform
import plistlib
import shlex
import shutil
import subprocess
import sys
import tempfile


REPOSITORY = 'https://github.com/federicobalm/geoexcel-map'


def run(*command, **kwargs):
    subprocess.run([str(arg) for arg in command], check=True, **kwargs)


def validate_platform():
    system = platform.system()
    if system == 'Darwin':
        if int(platform.mac_ver()[0].split('.')[0]) < 14:
            raise RuntimeError('Se requiere macOS 14 (Sonoma) o posterior para Chromium.')
    elif system == 'Linux':
        release = platform.freedesktop_os_release()
        supported = {'ubuntu': {'22.04', '24.04', '26.04'}, 'debian': {'12', '13'}}
        if release.get('VERSION_ID') not in supported.get(release.get('ID'), set()):
            raise RuntimeError('Instalacion automatica disponible para Ubuntu 22.04/24.04/26.04 y Debian 12/13.')
    else:
        raise RuntimeError('Este instalador es exclusivo de Linux y macOS.')
    return system


def desktop_quote(value):
    # freedesktop Exec has two layers of escaping; '%' is a field code there.
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\' + char)
    return '"' + value.replace('\\', '\\\\') + '"'


def desktop_value(value):
    return str(value).replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r')


def write_start_script(root):
    target = root / 'iniciar_geoexcel_map.command'
    target.write_text(
        '#!/bin/bash\n'
        f'exec {shlex.quote(str(root / ".venv/bin/python"))} '
        f'{shlex.quote(str(root / "scripts/run_unix.py"))}\n', encoding='utf-8')
    target.chmod(0o755)
    return target


def linux_shortcut(root, start):
    data_home = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    applications = data_home / 'applications'
    applications.mkdir(parents=True, exist_ok=True)
    target = applications / 'geoexcel-map.desktop'
    if target.exists() and 'X-GeoExcel-Managed=true' not in target.read_text(encoding='utf-8'):
        raise RuntimeError(f'Ya existe un acceso directo ajeno al instalador: {target}')
    content = (
        '[Desktop Entry]\nType=Application\nVersion=1.0\nName=GeoExcel Map\n'
        'Comment=Mapas y simulaciones para uso exclusivamente academico\n'
        f'Exec={desktop_quote(start)}\n'
        f'Path={desktop_value(root)}\n'
        f'Icon={desktop_value(root / "static/resources/logo/GeoExcel-Map.png")}\n'
        'Terminal=true\nCategories=Education;Science;\nX-GeoExcel-Managed=true\n'
    )
    target.write_text(content, encoding='utf-8')
    target.chmod(0o755)
    desktop = Path.home() / 'Desktop'
    if shutil.which('xdg-user-dir'):
        result = subprocess.run(['xdg-user-dir', 'DESKTOP'], capture_output=True, text=True, check=True)
        if result.stdout.strip():
            desktop = Path(result.stdout.strip())
    # XDG can intentionally disable the desktop by setting it to HOME.
    if desktop != Path.home():
        desktop.mkdir(parents=True, exist_ok=True)
        entry = desktop / 'GeoExcel Map.desktop'
        if not entry.exists() or 'X-GeoExcel-Managed=true' in entry.read_text(encoding='utf-8'):
            shutil.copy2(target, entry)
        else:
            print(f'No se reemplazo el acceso directo existente: {entry}')
    print('Acceso disponible en el menu de aplicaciones. En el escritorio puede requerir "Permitir lanzar".')
    return target


def mac_shortcut(root, start):
    bundle = Path.home() / 'Applications/GeoExcel Map.app'
    if bundle.exists() and not (bundle / '.geoexcel-managed').exists():
        raise RuntimeError(f'Ya existe una aplicacion ajena al instalador: {bundle}')
    executable_dir = bundle / 'Contents/MacOS'
    resources = bundle / 'Contents/Resources'
    executable_dir.mkdir(parents=True, exist_ok=True)
    resources.mkdir(parents=True, exist_ok=True)
    (bundle / '.geoexcel-managed').touch()
    executable = executable_dir / 'GeoExcelMap'
    executable.write_text(f'#!/bin/bash\nexec /usr/bin/open -a Terminal {shlex.quote(str(start))}\n', encoding='utf-8')
    executable.chmod(0o755)
    with tempfile.TemporaryDirectory(prefix='geoexcel-icon-') as temporary:
        iconset = Path(temporary) / 'GeoExcel.iconset'
        iconset.mkdir()
        image = root / 'static/resources/logo/GeoExcel-Map.png'
        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                name = f'icon_{size}x{size}' + ('@2x' if scale == 2 else '') + '.png'
                run('/usr/bin/sips', '-z', size * scale, size * scale, image, '--out', iconset / name, stdout=subprocess.DEVNULL)
        run('/usr/bin/iconutil', '-c', 'icns', iconset, '-o', resources / 'GeoExcel.icns')
    info = {
        'CFBundleName': 'GeoExcel Map', 'CFBundleDisplayName': 'GeoExcel Map',
        'CFBundleIdentifier': 'com.github.federicobalm.geoexcel-map',
        'CFBundleExecutable': 'GeoExcelMap', 'CFBundlePackageType': 'APPL',
        'CFBundleVersion': '3', 'CFBundleIconFile': 'GeoExcel.icns',
        'LSMinimumSystemVersion': '14.0', 'NSHighResolutionCapable': True,
    }
    with (bundle / 'Contents/Info.plist').open('wb') as stream:
        plistlib.dump(info, stream)
    desktop = Path.home() / 'Desktop'
    desktop.mkdir(exist_ok=True)
    link = desktop / 'GeoExcel Map.app'
    if not link.exists() and not link.is_symlink():
        link.symlink_to(bundle, target_is_directory=True)
    elif not (link.is_symlink() and link.resolve() == bundle.resolve()):
        print(f'No se reemplazo el elemento existente: {link}')
    print(f'Aplicacion disponible en {bundle}')
    return bundle


def install(root, source, uv):
    system = validate_platform()
    required = ('app', 'sample_data', 'static', 'scripts', 'launcher.py', 'app.py', 'requirements.txt', 'README.md', 'LICENSE')
    for name in required:
        if not (source / name).exists():
            raise RuntimeError(f'La descarga esta incompleta: falta {name}')
    print('[3/4] Instalando dependencias y Chromium...', flush=True)
    python = root / '.venv/bin/python'
    if not python.exists():
        run(uv, 'venv', '--python', sys.executable, root / '.venv')
    run(uv, 'pip', 'install', '--python', python, '-r', source / 'requirements.txt')
    if system == 'Linux' and os.environ.get('GEOEXCEL_SKIP_SYSTEM_DEPS') != '1':
        print('Linux puede solicitar tu contrasena de sudo para las bibliotecas de Chromium.', flush=True)
        run(python, '-m', 'playwright', 'install-deps', 'chromium')
    run(python, '-m', 'playwright', 'install', 'chromium')
    # Check browser startup, not just the presence of its executable.
    run(python, '-c', 'from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(); b.close(); p.stop()')
    for name in required:
        origin, target = source / name, root / name
        if origin.is_dir():
            shutil.copytree(origin, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(origin, target)
    run(python, '-c', 'from app.main import app; print("Aplicacion verificada.")', cwd=root)
    print('[4/4] Creando acceso directo...', flush=True)
    start = write_start_script(root)
    if system == 'Darwin':
        mac_shortcut(root, start)
    else:
        linux_shortcut(root, start)
    (root / '.setup-complete').touch()
    print(f'Listo. GeoExcel Map instalado en: {root}\nCierra la aplicacion y repite el mismo comando para actualizar.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--uv', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root / '.geoexcel-unix-install').is_file():
        raise RuntimeError('La carpeta no pertenece al instalador Unix.')
    with (root / '.operation.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Cierra GeoExcel Map o espera a que termine la otra instalacion.') from None
        install(root, args.source.resolve(), args.uv.resolve())


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
        print(f'ERROR: {error}\nCorrige el problema y vuelve a ejecutar el instalador.', file=sys.stderr)
        raise SystemExit(1)
