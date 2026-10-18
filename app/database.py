"""
EduDocs деректер базасымен жұмыс істеуге арналған ортақ модуль.

Базаға қосылу, схеманы құру, бастапқы деректерді енгізу және сұратым
нәтижесін кесте түрінде шығару функциялары осында жинақталған.
"""
import sqlite3
import sys
from pathlib import Path

import auth
import seed_data

# Windows жүйесінде (PyCharm, терминал) қазақ әріптері дұрыс шығуы үшін
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "edudocs.db"
SCHEMA_PATH = BASE_DIR / "schema.sql"

# ---------------------------------------------------------------------------
#  Қазақ тіліндегі мәтінмен жұмыс
# ---------------------------------------------------------------------------
KAZAKH_ALPHABET = "аәбвгғдеёжзийкқлмнңоөпрстуұүфхһцчшщъыіьэюя"
_KZ_ORDER = {ch: i for i, ch in enumerate(KAZAKH_ALPHABET)}


def kazakh_key(text):
    """Мәтінді қазақ әліпбиінің реті бойынша салыстыруға арналған кілт."""
    return [(_KZ_ORDER.get(ch, -1), ch) for ch in (text or "").lower()]


def kazakh_collation(a, b):
    """SQLite үшін KAZAKH салыстыру ережесі: -1, 0 немесе 1 қайтарады."""
    ka, kb = kazakh_key(a), kazakh_key(b)
    return (ka > kb) - (ka < kb)


def register_kazakh(conn):
    """kz_lower() функциясы мен KAZAKH салыстыру ережесін қосылымға тіркейді."""
    conn.create_function("kz_lower", 1, lambda s: s.lower() if isinstance(s, str) else s)
    conn.create_collation("KAZAKH", kazakh_collation)


# ---------------------------------------------------------------------------
#  Қосылу және базаны құру
# ---------------------------------------------------------------------------
def connect(db_path=DB_PATH):
    """Базаға қосылып, сыртқы кілттерді тексеруді және қазақша сұрыптауды қосады."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    register_kazakh(conn)
    return conn


def insert_seed_data(conn):
    """Бастапқы деректерді енгізеді: алдымен анықтамалықтар, кейін құжаттар."""
    cur = conn.cursor()
    cur.executemany("INSERT INTO departments VALUES (?, ?, ?)", seed_data.DEPARTMENTS)
    cur.executemany("INSERT INTO document_types VALUES (?, ?, ?, ?, ?)", seed_data.DOCUMENT_TYPES)
    cur.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?, ?)", seed_data.STUDENTS)
    cur.executemany(
        """INSERT INTO documents (reg_number, type_id, title, doc_date, academic_year,
                                  department_id, author, status, pages)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", seed_data.DOCUMENTS)
    cur.executemany(
        """INSERT INTO document_students (document_id, student_id, note)
           SELECT d.id, s.id, ? FROM documents d, students s
            WHERE d.reg_number = ? AND s.record_book = ?""",
        [(note, reg, book) for reg, book, note in seed_data.DOCUMENT_STUDENTS])
    cur.executemany(
        "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
        [(u, auth.hash_password(p), r, n) for u, p, r, n in seed_data.USERS])


def build_database(db_path=DB_PATH, overwrite=False):
    """Жаңа базаны құрады. overwrite=True болса, бұрынғы файл жойылады."""
    db_path = Path(db_path)
    if db_path.exists():
        if not overwrite:
            return db_path
        db_path.unlink()
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        with conn:                      # бір транзакция: не бәрі, не ештеңе
            insert_seed_data(conn)
    finally:
        conn.close()
    return db_path


def table_counts(conn):
    """Әр кестедегі жазбалар санын қайтарады."""
    names = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]
    return [(n, conn.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0]) for n in names]


# ---------------------------------------------------------------------------
#  Нәтижені консольге кесте түрінде шығару
# ---------------------------------------------------------------------------
def print_rows(cursor, title=None, max_width=46):
    """Курсордағы нәтижені тақырып жолы бар кесте ретінде басып шығарады."""
    headers = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    cells = [["—" if v is None else str(v)[:max_width] for v in row] for row in rows]
    widths = [max([len(h)] + [len(r[i]) for r in cells]) for i, h in enumerate(headers)]
    if title:
        print(f"\n▶ {title}")
    print("  " + " │ ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("  " + "─┼─".join("─" * w for w in widths))
    for r in cells:
        print("  " + " │ ".join(c.ljust(w) for c, w in zip(r, widths)))
    print(f"  Жолдар саны: {len(rows)}")
    return rows


if __name__ == "__main__":
    path = build_database(overwrite=True)
    with connect(path) as c:
        for name, count in table_counts(c):
            print(f"{name:<18} {count:>4}")
    print(f"\nДеректер базасы құрылды: {path}")
