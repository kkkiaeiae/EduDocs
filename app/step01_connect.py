"""
1-қадам. Деректер базасын құру, оған қосылу және ажырату.

SQLite серверсіз ДББЖ: деректер базасы — бір файл. sqlite3.connect()
файл жоқ болса, оны автоматты түрде құрады.
"""
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")   # Windows-та қазақ әріптері дұрыс шығуы үшін
DB_PATH = Path(__file__).resolve().parent / "edudocs.db"

print("=" * 64)
print("1-ҚАДАМ. ДЕРЕКТЕР БАЗАСЫН ҚҰРУ, ҚОСУ ЖӘНЕ АЖЫРАТУ")
print("=" * 64)
print("Python sqlite3 модулінің SQLite нұсқасы:", sqlite3.sqlite_version)
print("Деректер базасының файлы:", DB_PATH.name)
print("Файл бұрын болды ма:", "иә" if DB_PATH.exists() else "жоқ, қазір құрылады")

# 1. Қосылу. Connection объектісі базамен байланысты білдіреді
conn = sqlite3.connect(DB_PATH)
print("\nҚосылым ашылды:", type(conn).__name__)

# 2. Курсор — SQL командаларын жіберіп, нәтижесін алатын объект
cursor = conn.cursor()

# Сыртқы кілттерді тексеру SQLite-те әр қосылым үшін бөлек қосылады
cursor.execute("PRAGMA foreign_keys = ON")
cursor.execute("PRAGMA foreign_keys")
print("Сыртқы кілттерді тексеру:", "қосулы" if cursor.fetchone()[0] else "өшірулі")

cursor.execute("SELECT sqlite_version(), datetime('now', 'localtime')")
version, now = cursor.fetchone()
print(f"ДББЖ нұсқасы: {version}; ағымдағы уақыт: {now}")

cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'")
print("Базадағы кестелер саны:", cursor.fetchone()[0])
print("Файлдың өлшемі:", DB_PATH.stat().st_size, "байт")

# 3. Ажырату. Қосылым жабылғаннан кейін онымен жұмыс істеуге болмайды
conn.close()
print("\nҚосылым жабылды (conn.close()).")
try:
    conn.execute("SELECT 1")
except sqlite3.ProgrammingError as error:
    print("Жабық қосылымға сұратым жіберу әрекеті:", error)

# 4. Екінші базаны қосу (ATTACH) және ажырату (DETACH).
# Мысалы, ескі құжаттарды бөлек мұрағат файлында сақтауға болады
ARCHIVE_PATH = DB_PATH.with_name("archive.db")
conn = sqlite3.connect(DB_PATH)
conn.execute("ATTACH DATABASE ? AS archive", (str(ARCHIVE_PATH),))
names = [row[1] for row in conn.execute("PRAGMA database_list")]
print("\nATTACH-тан кейінгі базалар:", ", ".join(names))
conn.execute("DETACH DATABASE archive")
names = [row[1] for row in conn.execute("PRAGMA database_list")]
print("DETACH-тан кейінгі базалар:", ", ".join(names))
conn.close()

# 5. Контекст менеджері: блок сәтті аяқталса commit, қате болса rollback
with sqlite3.connect(DB_PATH) as conn:
    conn.execute("SELECT 1")
    print("with блогындағы қосылым сәтті жұмыс істеді.")
conn.close()
print("Қосылым қайта жабылды. 1-қадам аяқталды.")
