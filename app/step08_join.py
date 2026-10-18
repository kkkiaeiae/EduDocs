"""
8-қадам. Бірнеше кестеден іріктеу (JOIN).

INNER JOIN тек сәйкес жолдарды, LEFT JOIN сол жақ кестенің барлық жолдарын
қайтарады. «Көпке-көп» байланыс document_students кестесі арқылы оқылады.
"""
from database import connect, print_rows

print("=" * 64)
print("8-ҚАДАМ. БІРНЕШЕ КЕСТЕДЕН ІРІКТЕУ")
print("=" * 64)

conn = connect()
cur = conn.cursor()

# 1. INNER JOIN: үш кесте — құжат, оның түрі және бөлімшесі
print_rows(cur.execute(
    """SELECT d.reg_number, t.name AS түрі, dep.short_name AS бөлімше, d.status
         FROM documents d
         JOIN document_types t ON t.id = d.type_id
         JOIN departments dep  ON dep.id = d.department_id
        WHERE d.academic_year = '2026-2027' AND t.category = 'контингент'"""),
    "INNER JOIN: 2026–2027 оқу жылының контингент құжаттары")

# 2. Бөлімшелер бойынша құжаттар саны (JOIN + GROUP BY)
print_rows(cur.execute(
    """SELECT dep.name AS бөлімше, COUNT(d.id) AS құжат_саны
         FROM departments dep
         JOIN documents d ON d.department_id = dep.id
        GROUP BY dep.id ORDER BY құжат_саны DESC"""), "JOIN + GROUP BY")

# 3. «Көпке-көп»: білім алушыға қатысты барлық құжаттар
print_rows(cur.execute(
    """SELECT s.full_name, d.reg_number, ds.note
         FROM students s
         JOIN document_students ds ON ds.student_id = s.id
         JOIN documents d          ON d.id = ds.document_id
        WHERE s.record_book = '250101'"""), "«Көпке-көп»: Әбенова А. қатысты құжаттар")

# 4. LEFT JOIN: әр білім алушыға қатысты құжаттар саны (0 болса да шығады)
print_rows(cur.execute(
    """SELECT s.full_name, s.group_name, COUNT(ds.document_id) AS құжат_саны
         FROM students s
         LEFT JOIN document_students ds ON ds.student_id = s.id
        WHERE s.group_name IN ('ЖИТ-26-1', 'АЖ-25-1')
        GROUP BY s.id ORDER BY құжат_саны"""), "LEFT JOIN: білім алушылар және құжаттар саны")
conn.close()
print("\n8-қадам аяқталды.")
