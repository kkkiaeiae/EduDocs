"""
6-қадам. Деректерді сүзгілеу (WHERE).

Салыстыру операторлары, AND / OR, LIKE, BETWEEN, IN және IS NULL.
Қазақ тіліндегі мәтінді іздеу мәселесі де көрсетіледі.
"""
from database import connect, print_rows

print("=" * 64)
print("6-ҚАДАМ. ДЕРЕКТЕРДІ СҮЗГІЛЕУ")
print("=" * 64)

conn = connect()
cur = conn.cursor()

# 1. Теңдік және AND: келісуде тұрған силлабустар
print_rows(cur.execute(
    """SELECT reg_number, title, status FROM documents
        WHERE type_id = 1 AND status = 'келісуде'"""), "WHERE … AND …")

# 2. Салыстыру және OR: 3-курс немесе 1-курс білім алушылары
print_rows(cur.execute(
    """SELECT full_name, group_name, course FROM students
        WHERE course >= 3 OR course = 1"""), "WHERE … OR …")

# 3. BETWEEN: 2026 жылдың қыркүйегінде тіркелген құжаттар
print_rows(cur.execute(
    """SELECT reg_number, doc_date, status FROM documents
        WHERE doc_date BETWEEN '2026-09-01' AND '2026-09-30'"""), "BETWEEN: күндер аралығы")

# 4. IN: бірнеше мәннің бірі
print_rows(cur.execute(
    """SELECT reg_number, status FROM documents
        WHERE status IN ('жоба', 'келісуде')"""), "IN: жоба немесе келісуде")

# 5. IS NULL: e-mail енгізілмеген білім алушылар
print_rows(cur.execute("SELECT record_book, full_name FROM students WHERE email IS NULL"),
           "IS NULL: e-mail жоқ")

# 6. LIKE және қазақ әріптері.
#    SQLite LIKE операторы кириллицада бас және кіші әріптерді ажыратады,
#    сондықтан Python-да жазылған kz_lower() функциясы қолданылады
print("\n▶ LIKE: «СИЛЛАБУС» сөзін іздеу")
n1 = cur.execute("SELECT COUNT(*) FROM documents WHERE title LIKE '%СИЛЛАБУС%'").fetchone()[0]
n2 = cur.execute("SELECT COUNT(*) FROM documents "
                 "WHERE kz_lower(title) LIKE kz_lower('%СИЛЛАБУС%')").fetchone()[0]
print(f"  title LIKE '%СИЛЛАБУС%'                  → {n1} құжат")
print(f"  kz_lower(title) LIKE kz_lower('%СИЛЛАБУС%') → {n2} құжат")
conn.close()
print("\n6-қадам аяқталды.")
