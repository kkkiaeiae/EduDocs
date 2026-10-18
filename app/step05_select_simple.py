"""
5-қадам. Бір кестеден қарапайым іріктеулер (SELECT).

Барлық өрістерді немесе тек керекті өрістерді алу, өріске басқа атау беру
(AS), қайталанбайтын мәндер (DISTINCT), жолдар санын шектеу (LIMIT).
"""
from database import connect, print_rows

print("=" * 64)
print("5-ҚАДАМ. БІР КЕСТЕДЕН ҚАРАПАЙЫМ ІРІКТЕУЛЕР")
print("=" * 64)

conn = connect()
cur = conn.cursor()

# 1. Кестенің барлық өрістері
print_rows(cur.execute("SELECT * FROM departments"), "SELECT *: барлық бөлімшелер")

# 2. Таңдалған өрістер және AS арқылы берілген атаулар
print_rows(cur.execute(
    """SELECT code AS коды, name AS атауы, retention_years AS сақтау_жыл
         FROM document_types"""), "Таңдалған өрістер және AS: құжат түрлері")

# 3. DISTINCT: қайталанбайтын мәндер
print_rows(cur.execute("SELECT DISTINCT group_name AS тобы FROM students"),
           "DISTINCT: білім алушылардың топтары")

# 4. Есептелетін өріс және LIMIT: алғашқы 5 құжат
print_rows(cur.execute(
    """SELECT reg_number, substr(doc_date, 1, 4) AS жылы, pages, pages * 2 AS екі_жақты_бет
         FROM documents
        LIMIT 5"""), "Есептелетін өрістер және LIMIT 5")

# 5. fetchone(): бір мән
cur.execute("SELECT COUNT(*) FROM students")
print("\nfetchone(): білім алушылар саны =", cur.fetchone()[0])
conn.close()
print("5-қадам аяқталды.")
