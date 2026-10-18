"""
Repository класы: веб-қосымшаның барлық SQL сұратымдары осында жинақталған.

Рөлдер тек батырмалармен емес, осы деректер қабатында да тексеріледі:
қонақ тек «бекітілді» және «мұрағатта» мәртебесіндегі құжаттарды көреді,
ал деректерді өзгертетін әдістер оған PermissionError қатесін қайтарады.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

import database

STATUSES = ["жоба", "келісуде", "бекітілді", "мұрағатта"]
PUBLIC_STATUSES = ("бекітілді", "мұрағатта")


class Repository:
    def __init__(self, role="admin", db_path=database.DB_PATH):
        self.role = role
        self.db_path = db_path
        self.conn = database.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    @property
    def is_admin(self):
        return self.role == "admin"

    def require_admin(self):
        if not self.is_admin:
            raise PermissionError("Бұл әрекет тек әкімшіге рұқсат етілген.")

    def query(self, sql, params=()):
        return [dict(r) for r in self.conn.execute(sql, params)]

    # ----- анықтамалықтар ----------------------------------------------------
    def lookups(self):
        data = {
            "types": self.query("SELECT id, code, name, category FROM document_types ORDER BY code"),
            "departments": self.query("SELECT id, name, short_name FROM departments ORDER BY id"),
            "years": [r["academic_year"] for r in self.query(
                "SELECT DISTINCT academic_year FROM documents ORDER BY academic_year DESC")],
            "categories": [r["category"] for r in self.query(
                "SELECT DISTINCT category FROM document_types ORDER BY category COLLATE KAZAKH")],
            "statuses": STATUSES if self.is_admin else list(PUBLIC_STATUSES),
        }
        if self.is_admin:
            data["students"] = self.query(
                "SELECT id, record_book, full_name, group_name FROM students "
                "ORDER BY full_name COLLATE KAZAKH")
            data["groups"] = [r["group_name"] for r in self.query(
                "SELECT DISTINCT group_name FROM students ORDER BY group_name")]
        return data

    # ----- құжаттар тізілімі: барлық сүзгілер WHERE шартына айналады ----------
    WHERE = """ WHERE (:q = '' OR kz_lower(title) LIKE '%' || kz_lower(:q) || '%'
                                OR kz_lower(reg_number) LIKE '%' || kz_lower(:q) || '%')
                  AND (:category = '' OR category = :category)
                  AND (:type = '' OR type_code = :type)
                  AND (:year = '' OR academic_year = :year)
                  AND (:dep = '' OR department = :dep)
                  AND (:public = 0 OR status IN ('бекітілді', 'мұрағатта'))"""

    def _params(self, f):
        return {"q": (f.get("q") or "").strip(), "category": f.get("category") or "",
                "type": f.get("type") or "", "year": f.get("year") or "",
                "dep": f.get("dep") or "", "status": f.get("status") or "",
                "public": 0 if self.is_admin else 1}

    def registry(self, f):
        return self.query(
            "SELECT id, reg_number, doc_date, doc_type, category, title, department, author, status "
            "FROM v_registry" + self.WHERE + " AND (:status = '' OR status = :status) "
            "ORDER BY doc_date DESC, reg_number DESC", self._params(f))

    def status_counts(self, f):
        """Мәртебе батырмаларындағы сандар (GROUP BY)."""
        return {r["status"]: r["n"] for r in self.query(
            "SELECT status, COUNT(*) AS n FROM v_registry" + self.WHERE + " GROUP BY status",
            self._params(f))}

    def document(self, doc_id):
        rows = self.query(
            "SELECT d.*, t.name AS doc_type, t.category, t.retention_years, dep.name AS department "
            "FROM documents d JOIN document_types t ON t.id = d.type_id "
            "JOIN departments dep ON dep.id = d.department_id "
            "WHERE d.id = ? AND (? = 1 OR d.status IN ('бекітілді', 'мұрағатта'))",
            (doc_id, 1 if self.is_admin else 0))
        if not rows:
            raise LookupError("Құжат табылмады.")
        return rows[0]

    def document_students(self, doc_id):
        self.require_admin()            # білім алушылардың деректері — тек әкімшіге
        return self.query(
            "SELECT s.id, s.record_book, s.full_name, s.group_name, ds.note "
            "FROM document_students ds JOIN students s ON s.id = ds.student_id "
            "WHERE ds.document_id = ? ORDER BY s.full_name COLLATE KAZAKH", (doc_id,))

    def next_reg_number(self, type_id, year):
        """Келесі тіркеу нөмірі: түр коды, жыл және MAX() + 1."""
        code = self.conn.execute("SELECT code FROM document_types WHERE id = ?", (type_id,)).fetchone()
        if not code:
            return ""
        prefix = f"{code[0]}-{year}/"
        last = self.conn.execute(
            "SELECT MAX(CAST(substr(reg_number, ?) AS INTEGER)) FROM documents WHERE reg_number LIKE ?",
            (len(prefix) + 1, prefix + "%")).fetchone()[0]
        return f"{prefix}{(last or 0) + 1:03d}"

    # ----- өзгерту (тек әкімші) -----------------------------------------------
    FIELDS = ["reg_number", "type_id", "title", "doc_date", "academic_year",
              "department_id", "author", "status", "pages"]

    def save_document(self, data, doc_id=None):
        self.require_admin()
        values = [data.get(f) for f in self.FIELDS]
        with self.conn:                               # транзакция
            if doc_id is None:
                cur = self.conn.execute(
                    f"INSERT INTO documents ({', '.join(self.FIELDS)}) "
                    f"VALUES ({', '.join('?' * len(self.FIELDS))})", values)
                return cur.lastrowid
            self.conn.execute(
                f"UPDATE documents SET {', '.join(f + ' = ?' for f in self.FIELDS)} WHERE id = ?",
                values + [doc_id])
            return doc_id

    def set_status(self, doc_id, status):
        self.require_admin()
        with self.conn:
            self.conn.execute("UPDATE documents SET status = ? WHERE id = ?", (status, doc_id))

    def delete_document(self, doc_id):
        self.require_admin()
        with self.conn:                               # бекітілген құжатты триггер қорғайды
            self.conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

    def link_student(self, doc_id, student_id, note):
        self.require_admin()
        with self.conn:
            self.conn.execute("INSERT INTO document_students VALUES (?, ?, ?)",
                              (doc_id, student_id, note or None))

    def unlink_student(self, doc_id, student_id):
        self.require_admin()
        with self.conn:
            self.conn.execute("DELETE FROM document_students WHERE document_id = ? AND student_id = ?",
                              (doc_id, student_id))

    def backup(self):
        """Сақтық көшірме: sqlite3 Connection.backup() әдісі."""
        self.require_admin()
        folder = Path(self.db_path).parent / "backups"
        folder.mkdir(exist_ok=True)
        target = folder / f"edudocs_{datetime.now():%Y%m%d_%H%M%S}.db"
        copy = sqlite3.connect(target)
        self.conn.backup(copy)
        copy.close()
        return target.name

    # ----- білім алушылар (тек әкімші) -----------------------------------------
    def students(self, q="", group=""):
        self.require_admin()
        return self.query(
            "SELECT s.id, s.record_book, s.full_name, s.group_name, s.course, s.email, "
            "COUNT(ds.document_id) AS documents "
            "FROM students s LEFT JOIN document_students ds ON ds.student_id = s.id "
            "WHERE (:q = '' OR kz_lower(s.full_name) LIKE '%' || kz_lower(:q) || '%' "
            "       OR s.record_book LIKE :q || '%') "
            "AND (:group = '' OR s.group_name = :group) "
            "GROUP BY s.id ORDER BY s.full_name COLLATE KAZAKH",
            {"q": (q or "").strip(), "group": group or ""})

    def student_documents(self, student_id):
        self.require_admin()
        return self.query(
            "SELECT d.id, d.reg_number, d.doc_date, t.name AS doc_type, d.status, ds.note "
            "FROM document_students ds JOIN documents d ON d.id = ds.document_id "
            "JOIN document_types t ON t.id = d.type_id "
            "WHERE ds.student_id = ? ORDER BY d.doc_date DESC", (student_id,))

    # ----- басты бет --------------------------------------------------------------
    def dashboard(self):
        public = 0 if self.is_admin else 1
        cond = "WHERE (? = 0 OR status IN ('бекітілді', 'мұрағатта'))"
        data = {
            "statuses": {r["status"]: r["n"] for r in self.query(
                f"SELECT status, COUNT(*) AS n FROM documents {cond} GROUP BY status", (public,))},
            "categories": self.query(
                f"SELECT category AS name, COUNT(*) AS n FROM v_registry {cond} "
                "GROUP BY category ORDER BY n DESC", (public,)),
            "departments": self.query(
                f"SELECT department AS name, COUNT(*) AS n FROM v_registry {cond} "
                "GROUP BY department ORDER BY n DESC", (public,)),
        }
        if self.is_admin:
            data["pending"] = self.query(
                "SELECT id, reg_number, doc_type, status, "
                "CAST(julianday('now') - julianday(doc_date) AS INTEGER) AS days "
                "FROM v_registry WHERE status IN ('жоба', 'келісуде') ORDER BY doc_date")
        else:
            data["latest"] = self.query(
                "SELECT id, reg_number, doc_type, doc_date FROM v_registry "
                "WHERE status = 'бекітілді' ORDER BY doc_date DESC LIMIT 8")
        return data


# ===========================================================================
#  Дайын SQL есептері: (атауы, SQL мәтіні, қонаққа ашық па)
# ===========================================================================
REPORTS = [
    ("Бекітілген құжаттардың тізілімі (VIEW)",
     "SELECT reg_number, doc_date, doc_type, department, status\n"
     "  FROM v_registry\n WHERE status IN ('бекітілді', 'мұрағатта')\n ORDER BY doc_date DESC;", True),
    ("Құжат түрлері бойынша статистика (LEFT JOIN, GROUP BY)",
     "SELECT t.code, t.name, COUNT(d.id) AS саны\n  FROM document_types t\n"
     "  LEFT JOIN documents d ON d.type_id = t.id\n GROUP BY t.id\n ORDER BY саны DESC;", True),
    ("Бөлімшелер бойынша құжаттар (JOIN, GROUP BY, HAVING)",
     "SELECT dep.name AS бөлімше, COUNT(*) AS саны, SUM(d.pages) AS беттер\n"
     "  FROM documents d\n  JOIN departments dep ON dep.id = d.department_id\n"
     " GROUP BY dep.id\nHAVING COUNT(*) >= 5\n ORDER BY саны DESC;", True),
    ("2026–2027 оқу жылында құжаты жоқ түрлер (NOT EXISTS)",
     "SELECT t.code, t.name\n  FROM document_types t\n WHERE NOT EXISTS (\n"
     "       SELECT 1 FROM documents d\n        WHERE d.type_id = t.id\n"
     "          AND d.academic_year = '2026-2027');", True),
    ("Мұрағат құжаттарының сақтау мерзімі (күнмен есептеу)",
     "SELECT d.reg_number, d.doc_date, t.retention_years AS мерзімі,\n"
     "       date(d.doc_date, '+' || t.retention_years || ' years') AS аяқталуы\n"
     "  FROM documents d\n  JOIN document_types t ON t.id = d.type_id\n"
     " WHERE d.status = 'мұрағатта'\n ORDER BY аяқталуы;", True),
    ("Келісу сатысындағы құжаттар (WHERE, IN)",
     "SELECT reg_number, title, status, author\n  FROM documents\n"
     " WHERE status IN ('жоба', 'келісуде')\n ORDER BY doc_date;", False),
    ("Білім алушылар және құжаттар саны (LEFT JOIN)",
     "SELECT s.full_name, s.group_name, COUNT(ds.document_id) AS құжат\n"
     "  FROM students s\n  LEFT JOIN document_students ds ON ds.student_id = s.id\n"
     " GROUP BY s.id\n ORDER BY құжат DESC;", False),
    ("Топтар бойынша білім алушылар саны (GROUP BY)",
     "SELECT group_name, course, COUNT(*) AS саны\n  FROM students\n"
     " GROUP BY group_name, course\n ORDER BY course, group_name;", False),
]
