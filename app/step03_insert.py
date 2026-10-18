"""
3-қадам. Кестелерге деректерді енгізу (INSERT).

execute() бір жазбаны, executemany() бірнеше жазбаны енгізеді. Мәндер SQL
мәтініне тікелей жазылмайды, «?» параметрлері арқылы беріледі.
"""
import sqlite3

import auth
import seed_data
from database import DB_PATH, table_counts

print("=" * 64)
print("3-ҚАДАМ. ДЕРЕКТЕРДІ ЕНГІЗУ")
print("=" * 64)

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")
cursor = conn.cursor()

if cursor.execute("SELECT COUNT(*) FROM documents").fetchone()[0] > 0:
    conn.close()
    raise SystemExit("Деректер бұрын енгізілген. Алдымен step02_create_tables.py іске қосыңыз.")

# 1. Бір жазбаны execute() арқылы енгізу
cursor.execute("INSERT INTO departments (id, name, short_name) VALUES (?, ?, ?)",
               seed_data.DEPARTMENTS[0])
print("execute(): 1 бөлімше енгізілді →", seed_data.DEPARTMENTS[0][1])

# 2. Қалған жазбаларды executemany() арқылы енгізу.
#    Алдымен басқа кестелер сілтеме жасайтын анықтамалықтар толтырылады
cursor.executemany("INSERT INTO departments VALUES (?, ?, ?)", seed_data.DEPARTMENTS[1:])
cursor.executemany("INSERT INTO document_types VALUES (?, ?, ?, ?, ?)", seed_data.DOCUMENT_TYPES)
cursor.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?, ?)", seed_data.STUDENTS)
cursor.executemany(
    """INSERT INTO documents (reg_number, type_id, title, doc_date, academic_year,
                              department_id, author, status, pages)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", seed_data.DOCUMENTS)
print("executemany(): тіркелген құжаттар саны →", cursor.rowcount)

# 3. «Көпке-көп» байланыс: құжат пен білім алушының id мәндері
#    тіркеу нөмірі мен ID нөмірі бойынша табылады (INSERT ... SELECT)
cursor.executemany(
    """INSERT INTO document_students (document_id, student_id, note)
       SELECT d.id, s.id, ? FROM documents d, students s
        WHERE d.reg_number = ? AND s.record_book = ?""",
    [(note, reg, book) for reg, book, note in seed_data.DOCUMENT_STUDENTS])

# 4. Пайдаланушылар: құпиясөздің орнына оның хэші жазылады
cursor.executemany(
    "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?)",
    [(u, auth.hash_password(p), r, n) for u, p, r, n in seed_data.USERS])
conn.commit()
print("commit(): өзгерістер файлға сақталды.")

# 5. Қате деректер базаға түспейді: шектеулердің тексерісі
wrong_rows = [
    ("жоқ құжат түріне сілтеме (FOREIGN KEY)",
     "INSERT INTO documents (reg_number, type_id, title, doc_date, academic_year, department_id) "
     "VALUES ('ТЕСТ-1', 99, 'Тест', '2026-10-01', '2026-2027', 1)"),
    ("рұқсат етілмеген мәртебе (CHECK)",
     "INSERT INTO documents (reg_number, type_id, title, doc_date, academic_year, department_id, status) "
     "VALUES ('ТЕСТ-2', 1, 'Тест', '2026-10-01', '2026-2027', 1, 'белгісіз')"),
    ("тіркеу нөмірі қайталанды (UNIQUE)",
     "INSERT INTO documents (reg_number, type_id, title, doc_date, academic_year, department_id) "
     "VALUES ('СИЛ-2026/001', 1, 'Тест', '2026-10-01', '2026-2027', 1)"),
    ("курс 5 (CHECK)",
     "INSERT INTO students (record_book, full_name, group_name, course) "
     "VALUES ('999999', 'Тест', 'ЖИТ-25-1', 5)"),
    ("міндетті өріс бос (NOT NULL)",
     "INSERT INTO students (record_book, group_name, course) VALUES ('999998', 'ЖИТ-25-1', 1)"),
]
print("\nҚате деректерді енгізу әрекеттері:")
for label, sql in wrong_rows:
    try:
        cursor.execute(sql)
    except sqlite3.IntegrityError as error:
        print(f"  ✗ {label}: {error}")
conn.rollback()

print("\nКестелердегі жазбалар саны:")
total = 0
for name, count in table_counts(conn):
    print(f"  {name:<18}{count:>5}")
    total += count
print(f"  {'БАРЛЫҒЫ':<18}{total:>5}")
conn.close()
print("\n3-қадам аяқталды.")
