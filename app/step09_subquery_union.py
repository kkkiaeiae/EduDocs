"""
9-қадам. Кірістірілген сұратымдар және UNION.

Бір SELECT сұратымының нәтижесі екінші сұратымның ішінде қолданылады.
"""
from database import connect, print_rows

print("=" * 64)
print("9-ҚАДАМ. КІРІСТІРІЛГЕН СҰРАТЫМДАР ЖӘНЕ UNION")
print("=" * 64)

conn = connect()
cur = conn.cursor()

# 1. Бір мән қайтаратын ішкі сұратым: беттер саны орташадан көп құжаттар
avg = cur.execute("SELECT ROUND(AVG(pages), 1) FROM documents").fetchone()[0]
print(f"\nОрташа беттер саны: {avg}")
print_rows(cur.execute(
    """SELECT reg_number, pages FROM documents
        WHERE pages > (SELECT AVG(pages) FROM documents)
        ORDER BY pages DESC"""), "pages > (SELECT AVG(pages) …)")

# 2. IN (SELECT …): контингент бұйрықтарында аты бар білім алушылар
print_rows(cur.execute(
    """SELECT full_name, group_name FROM students
        WHERE id IN (SELECT ds.student_id
                       FROM document_students ds
                       JOIN documents d ON d.id = ds.document_id
                      WHERE d.type_id = 6 AND d.academic_year = '2026-2027')"""),
    "IN (SELECT …): 2026–2027 оқу жылының бұйрықтарындағы білім алушылар")

# 3. NOT EXISTS: 2026–2027 оқу жылында әлі бірде-бір құжаты жоқ құжат түрлері
print_rows(cur.execute(
    """SELECT t.code, t.name FROM document_types t
        WHERE NOT EXISTS (SELECT 1 FROM documents d
                           WHERE d.type_id = t.id AND d.academic_year = '2026-2027')"""),
    "NOT EXISTS: 2026–2027 оқу жылында құжаты жоқ түрлер")

# 4. UNION: екі сұратымның нәтижесін біріктіру (қайталанатын жолдар алынады)
print_rows(cur.execute(
    """SELECT author AS аты_жөні, 'қызметкер' AS рөлі FROM documents
        WHERE author IS NOT NULL AND department_id = 1
       UNION
       SELECT full_name, 'білім алушы' FROM students WHERE course = 3
       ORDER BY рөлі, аты_жөні"""), "UNION: ЖИТ қызметкерлері және 3-курс білім алушылары")
conn.close()
print("\n9-қадам аяқталды.")
