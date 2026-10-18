"""
2-қадам. Кестелерді құру және олардың арасындағы байланыстарды орнату.

Барлық CREATE командалары schema.sql файлында жазылған. Скрипт оларды
орындап, құрылған кестелерді және сыртқы кілттерді экранға шығарады.
"""
import sqlite3

from database import DB_PATH, SCHEMA_PATH

print("=" * 64)
print("2-ҚАДАМ. КЕСТЕЛЕРДІ ҚҰРУ ЖӘНЕ БАЙЛАНЫСТАРДЫ ОРНАТУ")
print("=" * 64)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Скрипт қайта іске қосылса, бұрынғы кестелер жойылады
cursor.execute("PRAGMA foreign_keys = OFF")
for kind, name in cursor.execute(
        "SELECT type, name FROM sqlite_master WHERE type IN ('view', 'table')").fetchall():
    cursor.execute(f'DROP {kind.upper()} IF EXISTS "{name}"')

# schema.sql файлындағы барлық командаларды орындау
cursor.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
cursor.execute("PRAGMA foreign_keys = ON")

# Құрылған нысандар (жүйелік каталог sqlite_master арқылы)
labels = {"table": "Кестелер", "index": "Индекстер", "view": "Көріністер", "trigger": "Триггерлер"}
for kind, label in labels.items():
    names = [r[0] for r in cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = ? AND name NOT LIKE 'sqlite_%' "
        "ORDER BY rowid", (kind,))]
    print(f"{label} ({len(names)}): {', '.join(names)}")

# Кестелер арасындағы байланыстар: PRAGMA foreign_key_list
print("\nСыртқы кілттер (кестелер арасындағы байланыстар):")
for table in ("documents", "document_students"):
    fks = cursor.execute(f"PRAGMA foreign_key_list({table})").fetchall()
    for fk in sorted(fks, key=lambda r: -r[0]):        # жариялану ретімен
        # fk: (id, seq, кесте, өріс, сілтеме өрісі, on_update, on_delete, match)
        print(f"  {table + '.' + fk[3]:<30} → {fk[2]}.{fk[4]}   [ON DELETE {fk[6]}]")

# documents кестесінің құрылымы: PRAGMA table_info
print("\ndocuments кестесінің құрылымы:")
print(f"  {'өріс':<15}{'типі':<9}{'NOT NULL':<10}PK")
for cid, name, col_type, notnull, default, pk in cursor.execute("PRAGMA table_info(documents)"):
    print(f"  {name:<15}{col_type:<9}{'иә' if notnull else '—':<10}{'PK' if pk else ''}")

# ALTER TABLE және DROP TABLE командалары уақытша кестеде көрсетіледі
cursor.execute("CREATE TABLE temp_demo (id INTEGER PRIMARY KEY, title TEXT)")
cursor.execute("ALTER TABLE temp_demo ADD COLUMN note TEXT")
print("\nALTER TABLE: temp_demo кестесіне note өрісі қосылды →",
      [r[1] for r in cursor.execute("PRAGMA table_info(temp_demo)")])
cursor.execute("DROP TABLE temp_demo")
print("DROP TABLE: temp_demo кестесі жойылды.")

conn.commit()
conn.close()
print("\n2-қадам аяқталды.")
