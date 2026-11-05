"""Real Unix install/update/launch smoke test, using an isolated student HOME."""
import os
from pathlib import Path
import platform
import signal
import socket
import subprocess
import tarfile
import tempfile
import time
import urllib.request


def main():
    source = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='geoexcel-unix-') as temporary:
        work = Path(temporary)
        home = work / 'Student Home'
        home.mkdir()
        root = home / 'GeoExcel con espacios'
        archive = work / 'source.tar.gz'
        with tarfile.open(archive, 'w:gz') as bundle:
            for name in ('app', 'sample_data', 'static', 'scripts', 'launcher.py', 'app.py', 'requirements.txt', 'README.md', 'LICENSE'):
                bundle.add(source / name, arcname='geoexcel-map-main/' + name,
                           filter=lambda item: None if '__pycache__' in item.name or item.name.endswith('.pyc') else item)
        env = {**os.environ, 'HOME': str(home), 'XDG_DATA_HOME': str(home / '.local/share'),
               'GEOEXCEL_INSTALL_DIR': str(root), 'GEOEXCEL_SOURCE_ARCHIVE': str(archive)}
        command = ['bash', str(source / 'scripts/install.sh')]
        subprocess.run(command, env=env, check=True)
        assert (root / '.setup-complete').is_file()
        if platform.system() == 'Darwin':
            import plistlib
            app = home / 'Applications/GeoExcel Map.app'
            with (app / 'Contents/Info.plist').open('rb') as stream:
                assert plistlib.load(stream)['CFBundleExecutable'] == 'GeoExcelMap'
            assert (app / 'Contents/Resources/GeoExcel.icns').stat().st_size > 0
            assert (home / 'Desktop/GeoExcel Map.app').resolve() == app
        else:
            desktop = home / '.local/share/applications/geoexcel-map.desktop'
            assert desktop.is_file() and os.access(desktop, os.X_OK)
            if subprocess.run(['bash', '-c', 'command -v desktop-file-validate'], capture_output=True).returncode == 0:
                subprocess.run(['desktop-file-validate', str(desktop)], check=True)
        (root / 'data').mkdir(exist_ok=True)
        (root / 'data/student.txt').write_text('preserved', encoding='utf-8')
        (root / '.env').write_text('APP_ENV=testing\n', encoding='utf-8')
        subprocess.run(command, env=env, check=True)
        assert (root / 'data/student.txt').read_text() == 'preserved'
        assert (root / '.env').read_text() == 'APP_ENV=testing\n'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        process = subprocess.Popen([str(root / 'iniciar_geoexcel_map.command')], env={
            **env, 'APP_HOST': '127.0.0.1', 'APP_PORT': str(port), 'BROWSER': 'true',
        }, start_new_session=True)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise AssertionError('Launcher exited before readiness')
                try:
                    with opener.open(f'http://127.0.0.1:{port}/health/ready', timeout=1) as response:
                        assert response.status == 200
                    break
                except OSError:
                    time.sleep(.2)
            else:
                raise AssertionError('Server not ready')
            # A running classroom session must prevent code/dependency updates.
            blocked = subprocess.run([str(root / '.venv/bin/python'), str(root / 'scripts/install_unix.py'),
                                      '--root', str(root), '--source', str(source), '--uv', str(root / 'tools/uv')],
                                     env=env, capture_output=True, text=True)
            assert blocked.returncode != 0 and 'Cierra GeoExcel Map' in blocked.stderr
        finally:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        with socket.socket() as sock:
            assert sock.connect_ex(('127.0.0.1', port)) != 0, 'Server leaked after launcher exit'
        print('PASS Unix install, update, data preservation, desktop entry, startup, update lock and shutdown.')


if __name__ == '__main__':
    main()
