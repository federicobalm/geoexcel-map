"""Desktop entry point on Unix; own server shutdown and installation lock."""
import fcntl
from pathlib import Path
import os
import signal
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    sys.path.insert(0, str(root))
    with (root / '.operation.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('GeoExcel Map ya esta abierto o se esta actualizando.', flush=True)
            return 1

        def stop(_signum, _frame):
            raise KeyboardInterrupt

        for signum in (signal.SIGTERM, signal.SIGHUP):
            signal.signal(signum, stop)
        import launcher
        return launcher.main()


if __name__ == '__main__':
    raise SystemExit(main())
