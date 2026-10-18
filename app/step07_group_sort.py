"""
7-қадам. Жолдарды сұрыптау (ORDER BY) және топтау (GROUP BY, HAVING).

Агрегаттық функциялар: COUNT, SUM, AVG, MIN, MAX.
Қазақ әліпбиі бойынша дұрыс сұрыптау үшін KAZAKH салыстыру ережесі қолданылады.
"""
from database import connect, print_rows

print("=" * 64)
print("7-ҚАДАМ. СҰРЫПТАУ ЖӘНЕ ТОПТАУ")
print("=" * 64)

conn = connect()
cur = conn.cursor()

# 1. ORDER BY бірнеше өріс бойынша: курс кему ретімен, сосын топ бойынша
print_rows(cur.execute(
    """SELECT group_name, course, COUNT(*) AS саны FROM students
        GROUP BY group_name, course
        ORDER BY course DESC, group_name"""), "ORDER BY course DESC, group_name")

# 2. Қазақ әріптері: әдепкі BINARY реті мен KAZAKH реті
names = "SELECT full_name FROM students WHERE group_name = 'ЖИТ-24-1' ORDER BY full_name"
binary = [r[0] for r in cur.execute(names)]
kazakh = [r[0] for r in cur.execute(names + " COLLATE KAZAKH")]
print("\n▶ ORDER BY full_name: BINARY және COLLATE KAZAKH")
for a, b in zip(binary, kazakh):
    print(f"  {a:<20} │ {b}")

# 3. GROUP BY: мәртебелер бойынша құжаттар саны
print_rows(cur.execute(
    """SELECT status AS мәртебесі, COUNT(*) AS саны FROM documents
        GROUP BY status ORDER BY саны DESC"""), "GROUP BY status")

# 4. GROUP BY + агрегаттық функциялар: бөлімшелер бойынша беттер
print_rows(cur.execute(
    """SELECT department_id, COUNT(*) AS құжат, SUM(pages) AS барлық_бет,
              ROUND(AVG(pages), 1) AS орташа_бет, MIN(doc_date) AS ең_ерте, MAX(doc_date) AS ең_кеш
         FROM documents
        GROUP BY department_id"""), "SUM, AVG, MIN, MAX")

# 5. HAVING: 5-тен көп құжаты бар құжат түрлері
print_rows(cur.execute(
    """SELECT type_id, COUNT(*) AS саны FROM documents
        GROUP BY type_id
       HAVING COUNT(*) > 5"""), "HAVING COUNT(*) > 5")
conn.close()
print("\n7-қадам аяқталды.")
