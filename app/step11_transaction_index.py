"""
11-қадам. Транзакциялар (COMMIT, ROLLBACK) және индекстер.

Транзакция — бірге орындалатын әрекеттер тобы: не бәрі сақталады,
не ештеңе сақталмайды. Индекс іздеуді жылдамдатады.
"""
import sqlite3

from database import DB_PATH

print("=" * 64)
print("11-ҚАДАМ. ТРАНЗАКЦИЯЛАР ЖӘНЕ ИНДЕКСТЕР")
print("=" * 64)

# isolation_level=None: транзакцияны BEGIN командасымен өзіміз бастаймыз
conn = sqlite3.connect(DB_PATH, isolation_level=None, cached_statements=0)
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()
count = lambda: cur.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

# 1. COMMIT: ауысып келген білім алушы туралы бұйрық бекітіледі және
#    оның e-mail мекенжайы енгізіледі — екі кестедегі өзгеріс бірге сақталады
print("\n▶ 1. BEGIN … COMMIT")
cur.execute("BEGIN")
cur.execute("UPDATE documents SET status = 'бекітілді' WHERE reg_number = 'БК-2026/004'")
cur.execute("UPDATE students SET email = 's250206@univ.example.com' WHERE record_book = '250206'")
cur.execute("COMMIT")
print("  Бұйрықтың мәртебесі:",
      cur.execute("SELECT status FROM documents WHERE reg_number = 'БК-2026/004'").fetchone()[0])
print("  Білім алушының e-mail:",
      cur.execute("SELECT email FROM students WHERE record_book = '250206'").fetchone()[0])

# 2. ROLLBACK: екінші әрекетте қате болса, біріншісі де болдырылмайды
print("\n▶ 2. BEGIN … ROLLBACK")
before = count()
try:
    cur.execute("BEGIN")
    cur.execute(
        """INSERT INTO documents (reg_number, type_id, title, doc_date, academic_year, department_id)
           VALUES ('БК-2026/006', 6, 'Грант беру туралы', '2026-10-02', '2026-2027', 4)""")
    print("  1-әрекет: бұйрық енгізілді")
    cur.execute("INSERT INTO document_students VALUES (?, 999, 'грант')", (cur.lastrowid,))
    cur.execute("COMMIT")
except sqlite3.IntegrityError as error:
    cur.execute("ROLLBACK")
    print("  2-әрекеттің қатесі:", error, "→ ROLLBACK")
print(f"  Құжаттар саны: транзакцияға дейін {before}, кейін {count()}")

# 3. EXPLAIN QUERY PLAN: сұратым индексті қолдана ма?
print("\n▶ 3. EXPLAIN QUERY PLAN")
query = "SELECT reg_number FROM documents WHERE doc_date = '2026-09-10'"
print("  Индекспен: ", cur.execute("EXPLAIN QUERY PLAN " + query).fetchone()[-1])
cur.execute("DROP INDEX idx_documents_date")
print("  Индекссіз: ", cur.execute("EXPLAIN QUERY PLAN " + query).fetchone()[-1])
cur.execute("CREATE INDEX idx_documents_date ON documents(doc_date)")
conn.close()


print("\n11-қадам аяқталды.")
