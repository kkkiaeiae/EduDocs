"""
Барлық қадамдарды (step01 … step12) ретімен орындайды.

Деректер базасы нөлден қайта құрылады, әр скрипттің экранға шығарған
нәтижесі outputs/ бумасына мәтіндік файл ретінде сақталады.
"""
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "outputs"
OUT_DIR.mkdir(exist_ok=True)

db = BASE_DIR / "edudocs.db"
if db.exists():
    db.unlink()
    print("Бұрынғы edudocs.db жойылды.")

env = dict(os.environ, PYTHONIOENCODING="utf-8")
for script in sorted(BASE_DIR.glob("step*.py")):
    result = subprocess.run([sys.executable, script.name], cwd=BASE_DIR, env=env,
                            capture_output=True, text=True, encoding="utf-8")
    (OUT_DIR / f"{script.stem}.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    state = "сәтті" if result.returncode == 0 else f"ҚАТЕ (код {result.returncode})"
    print(f"{script.name:<32} {state}")
print(f"\nНәтижелер: {OUT_DIR}")
