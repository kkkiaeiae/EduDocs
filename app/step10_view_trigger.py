"""
10-қадам. Көрініс (VIEW) және триггер (TRIGGER).

v_registry көрінісі үш кестені біріктіретін сақталған SELECT сұратымы.
trg_protect_approved триггері бекітілген құжаттың жойылуына жол бермейді.
"""
import sqlite3

from database import connect, print_rows

print("=" * 64)
print("10-ҚАДАМ. КӨРІНІС ЖӘНЕ ТРИГГЕР")
print("=" * 64)

conn = connect()
cur = conn.cursor()

# 1. Көріністің мәтіні жүйелік каталогта сақталады
sql = cur.execute("SELECT sql FROM sqlite_master WHERE name = 'v_registry'").fetchone()[0]
print("\nv_registry көрінісінің SQL мәтіні:\n" + sql)

# 2. Көріністі кесте сияқты қолдану: JOIN жазудың қажеті жоқ
print_rows(cur.execute(
    """SELECT reg_number, doc_type, department, status FROM v_registry
        WHERE category = 'аттестаттау' AND academic_year = '2025-2026'
        ORDER BY reg_number"""), "SELECT … FROM v_registry")

# 3. Жаңа уақытша көрініс: санаттар бойынша статистика
cur.execute("""CREATE TEMP VIEW v_category_stats AS
               SELECT category, COUNT(*) AS саны FROM v_registry GROUP BY category""")
print_rows(cur.execute("SELECT * FROM v_category_stats ORDER BY саны DESC"),
           "CREATE TEMP VIEW v_category_stats")

# 4. Триггердің жұмысы
print("\n▶ trg_protect_approved триггері")
for reg in ("ВЕД-2025/001", "КЖ-2026/004"):
    status = cur.execute("SELECT status FROM documents WHERE reg_number = ?", (reg,)).fetchone()[0]
    try:
        cur.execute("DELETE FROM documents WHERE reg_number = ?", (reg,))
        print(f"  {reg} ({status}): жоюға рұқсат етілді")
    except sqlite3.IntegrityError as error:
        print(f"  {reg} ({status}): ✗ {error}")
conn.rollback()                      # мысал болғандықтан, база өзгертілмейді
print("  rollback(): жойылған жоба құжаты қайтарылды")
conn.close()
print("\n10-қадам аяқталды.")
