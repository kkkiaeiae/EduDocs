"""
EduDocs веб-қосымшасын іске қосу.

PyCharm-да осы файлды Run арқылы іске қосыңыз немесе терминалда:  python start.py
Браузер http://127.0.0.1:8770/ адресін өзі ашады.
Кіру: admin / Admin2026 (әкімші), qonaq / Qonaq2026 (қонақ).
"""
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent / "app"

if __name__ == "__main__":
    if sys.version_info < (3, 9):
        sys.exit("Python 3.9 немесе жаңа нұсқасы қажет")
    try:
        subprocess.run([sys.executable, "app.py", *sys.argv[1:]], cwd=APP_DIR, check=False)
    except KeyboardInterrupt:
        pass
