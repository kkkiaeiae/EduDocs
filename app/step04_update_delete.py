"""
4-қадам. Деректерді өзгерту (UPDATE) және жою (DELETE).

Жаңа құжат тіркеліп, мәртебесі өзгертіледі, содан кейін жойылады.
Сыртқы кілттердің CASCADE және RESTRICT ережелері мен триггердің
жұмысы да тексеріледі.
"""
import sqlite3

from database import DB_PATH, print_rows

print("=" * 64)
print("4-ҚАДАМ. ДЕРЕКТЕРДІ ӨЗГЕРТУ ЖӘНЕ ЖОЮ")
print("=" * 64)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")
cur = conn.cursor()


def show(reg):
    print_rows(cur.execute(
        "SELECT reg_number, status, pages FROM documents WHERE reg_number = ?", (reg,)))


# 1. Жаңа құжат тіркеу және оған екі білім алушыны байланыстыру
cur.execute(
    """INSERT INTO documents (reg_number, type_id, title, doc_date, academic_year,
                              department_id, author)
       VALUES ('БК-2026/005', 6, 'Білім алушыларды басқа топқа ауыстыру туралы',
               '2026-10-01', '2026-2027', 4, 'Кенжебаева Ә.Н.')""")
new_id = cur.lastrowid
cur.executemany("INSERT INTO document_students VALUES (?, ?, 'ЖИТ-25-1 тобына')",
                [(new_id, 9), (new_id, 10)])
conn.commit()
print("\n▶ Жаңа құжат тіркелді (мәртебесі әдепкі бойынша «жоба»):")
show("БК-2026/005")

# 2. UPDATE: бір жазбаның мәртебесі мен беттер санын өзгерту
cur.execute("UPDATE documents SET status = 'келісуде', pages = 2 WHERE reg_number = 'БК-2026/005'")
conn.commit()
print("\n▶ UPDATE: мәртебе «келісуде», беттер саны 2:")
show("БК-2026/005")

# 3. UPDATE бірнеше жазбаға: беттер саны жоқ жобаларға 1 бет жазылады
cur.execute("UPDATE documents SET pages = 1 WHERE status = 'жоба' AND pages IS NULL")
print(f"\n▶ UPDATE бірнеше жолға: {cur.rowcount} құжаттың беттер саны толтырылды")
conn.rollback()                      # мысал ғана: өзгеріс сақталмайды
print("  rollback(): бұл өзгеріс кері қайтарылды")

# 4. DELETE + ON DELETE CASCADE: құжат жойылғанда байланыс жолдары да жойылады
links = "SELECT COUNT(*) FROM document_students WHERE document_id = ?"
print("\n▶ DELETE: БК-2026/005 құжатын жою")
print("  Жоюға дейін байланысқан білім алушылар:", cur.execute(links, (new_id,)).fetchone()[0])
cur.execute("DELETE FROM documents WHERE reg_number = 'БК-2026/005'")
conn.commit()
print("  Жойылған құжаттар:", cur.rowcount)
print("  Жойылғаннан кейін байланыс жолдары (CASCADE):", cur.execute(links, (new_id,)).fetchone()[0])

# 5. ON DELETE RESTRICT: құжаттары бар бөлімшені жоюға болмайды
print("\n▶ RESTRICT: құжаттары бар бөлімшені жою әрекеті")
try:
    cur.execute("DELETE FROM departments WHERE short_name = 'МАТ'")
except sqlite3.IntegrityError as error:
    print("  ✗", error)

# 6. Триггер: бекітілген құжатты жоюға тыйым салынған
print("\n▶ Триггер: бекітілген СИЛ-2026/001 құжатын жою әрекеті")
try:
    cur.execute("DELETE FROM documents WHERE reg_number = 'СИЛ-2026/001'")
except sqlite3.IntegrityError as error:
    print("  ✗", error)
conn.rollback()

print("\nҚұжаттар саны:", cur.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
conn.close()
print("4-қадам аяқталды.")
