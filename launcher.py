"""Start the local server and open its browser only after readiness succeeds."""
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

from app.config import settings


def wait_until_ready(process, url, timeout=90):
    deadline = time.monotonic() + timeout
    # Local health checks must not be sent through a system HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("El servidor se cerro antes de estar listo.")
        try:
            with opener.open(f"{url}/health/ready", timeout=1) as response:
                if response.status == 200 and json.load(response).get("status") == "ready":
                    return
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            pass
        time.sleep(0.25)
    raise RuntimeError("El servidor no estuvo listo dentro de 90 segundos.")


def main():
    host = settings.app_host
    browser_host = "127.0.0.1" if host == "0.0.0.0" else "::1" if host == "::" else host
    url_host = f"[{browser_host}]" if ":" in browser_host else browser_host
    url = f"http://{url_host}:{settings.app_port}"
    try:
        with socket.create_connection((browser_host, settings.app_port), timeout=0.5):
            print(f"El puerto {settings.app_port} ya esta ocupado. Cerra la instancia anterior antes de iniciar.")
            return 1
    except OSError:
        pass
    # No reload supervisor for the classroom launcher: one owned server process.
    process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", "app.main:app", "--host", host,
        "--port", str(settings.app_port), "--no-use-colors",
    ], cwd=settings.project_root)
    try:
        print(f"Esperando que GeoExcel Map este listo en {url}...", flush=True)
        wait_until_ready(process, url)
        print(f"Sistema listo. Abriendo {url}", flush=True)
        webbrowser.open(url)
        return process.wait()
    except KeyboardInterrupt:
        return 0
    except RuntimeError as exc:
        print(f"ERROR: {exc}", flush=True)
        return 1
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
