"""
EduDocs — мемлекеттік ЖОО-дағы оқу үдерісіне қатысты құжаттарды есепке алу жүйесі.

Веб-қосымша: Python стандартты кітапханасы (http.server, json, sqlite3) + SQLite.
Сервер компьютердің өзінде (127.0.0.1) іске қосылады, интерфейс браузерде ашылады.

Іске қосу (PyCharm немесе терминал):  python app.py
"""
import csv
import io
import json
import secrets
import sqlite3
import sys
import threading
import webbrowser
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import auth
import database
from repository import REPORTS, STATUSES, Repository

HOST, PORT = "127.0.0.1", 8770
WEB_DIR = Path(__file__).resolve().parent / "web"
FILE_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
              ".js": "application/javascript; charset=utf-8", ".woff2": "font/woff2",
              ".txt": "text/plain; charset=utf-8"}
SESSIONS = {}                      # сессия белгісі (cookie) → пайдаланушы


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):                 # консольді әр сұраныспен толтырмау үшін
        pass

    # ----- көмекші әдістер ---------------------------------------------------
    def current_user(self):
        jar = cookies.SimpleCookie(self.headers.get("Cookie", ""))
        token = jar["session"].value if "session" in jar else None
        return token, SESSIONS.get(token)

    def send(self, body, content_type, status=200, extra=()):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in extra:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data, status=200, extra=()):
        self.send(json.dumps(data, ensure_ascii=False).encode("utf-8"),
                  "application/json; charset=utf-8", status, extra)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            raise HttpError(400, "JSON пішімі дұрыс емес.")

    def handle_api(self, method):
        url = urlparse(self.path)
        params = {k: v[0] for k, v in parse_qs(url.query).items()}
        token, user = self.current_user()
        try:
            if url.path == "/api/login" and method == "POST":
                return self.login(self.read_json())
            if url.path == "/api/me":
                return self.send_json({"user": user})
            if user is None:
                raise HttpError(401, "Алдымен жүйеге кіріңіз.")
            if url.path == "/api/logout":
                SESSIONS.pop(token, None)
                return self.send_json({"user": None})
            repo = Repository(user["role"])
            try:
                if method == "GET":
                    result = self.route_get(repo, url.path, params)
                else:
                    result = self.route_post(repo, url.path, self.read_json())
            finally:
                repo.close()
            if isinstance(result, tuple):         # CSV файлы
                return self.send(*result)
            self.send_json(result)
        except HttpError as error:
            self.send_json({"error": str(error)}, error.status)
        except PermissionError as error:
            self.send_json({"error": str(error)}, 403)
        except LookupError as error:
            self.send_json({"error": str(error)}, 404)
        except sqlite3.Error as error:            # ДББЖ шектеулері мен триггер хабарлары
            self.send_json({"error": f"Деректер базасының қатесі: {error}"}, 409)

    def login(self, data):
        conn = database.connect()
        try:
            user = auth.authenticate(conn, data.get("username"), data.get("password"))
        finally:
            conn.close()
        if user is None:
            raise HttpError(401, "Логин немесе құпиясөз қате.")
        token = secrets.token_urlsafe(32)
        SESSIONS[token] = user
        self.send_json({"user": user}, extra=[(
            "Set-Cookie", f"session={token}; HttpOnly; SameSite=Strict; Path=/")])

    # ----- GET сұраныстары -----------------------------------------------------
    def route_get(self, repo, path, p):
        parts = path.strip("/").split("/")[1:]       # /api/documents/5 → ["documents", "5"]
        if not parts:
            raise HttpError(404, "Мұндай бет жоқ.")
        if parts == ["lookups"]:
            return repo.lookups()
        if parts == ["dashboard"]:
            return repo.dashboard()
        if parts == ["documents"]:
            return {"rows": repo.registry(p), "counts": repo.status_counts(p)}
        if parts[0] == "documents" and len(parts) == 2:
            doc_id = int(parts[1])
            data = {"document": repo.document(doc_id)}
            if repo.is_admin:
                data["students"] = repo.document_students(doc_id)
            return data
        if parts == ["next-number"]:
            return {"reg_number": repo.next_reg_number(p.get("type"), p.get("year", "")[:4])}
        if parts == ["students"]:
            return repo.students(p.get("q", ""), p.get("group", ""))
        if parts[0] == "students" and len(parts) == 2:
            return repo.student_documents(int(parts[1]))
        if parts == ["reports"]:
            return [{"id": i, "title": t, "sql": s} for i, (t, s, public) in enumerate(REPORTS)
                    if public or repo.is_admin]
        if parts == ["export.csv"]:
            out = io.StringIO()
            writer = csv.writer(out, delimiter=";")
            writer.writerow(["Тіркеу №", "Күні", "Түрі", "Атауы", "Бөлімше", "Жауапты", "Мәртебесі"])
            for r in repo.registry(p):
                writer.writerow([r["reg_number"], r["doc_date"], r["doc_type"], r["title"],
                                 r["department"], r["author"] or "", r["status"]])
            return (out.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", 200,
                    [("Content-Disposition", "attachment; filename=edudocs.csv")])
        raise HttpError(404, "Мұндай бет жоқ.")

    # ----- POST сұраныстары ----------------------------------------------------
    def route_post(self, repo, path, data):
        parts = path.strip("/").split("/")[1:]
        if not parts:
            raise HttpError(404, "Мұндай әрекет жоқ.")
        doc_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        action = parts[2] if len(parts) > 2 else ""
        if parts[0] == "documents" and action in ("", "save"):
            doc = {f: data.get(f) for f in Repository.FIELDS}
            for f in ("type_id", "department_id", "pages"):
                doc[f] = int(doc[f]) if str(doc[f] or "").isdigit() else None
            for f in ("reg_number", "title", "author", "doc_date", "academic_year"):
                doc[f] = (doc[f] or "").strip() or None
            doc["status"] = doc["status"] or "жоба"
            missing = [n for f, n in (("reg_number", "тіркеу нөмірі"), ("type_id", "құжат түрі"),
                                      ("title", "атауы"), ("doc_date", "күні"),
                                      ("academic_year", "оқу жылы"), ("department_id", "бөлімше"))
                       if not doc[f]]
            if missing:
                raise HttpError(400, "Міндетті өрістер толтырылмаған: " + ", ".join(missing))
            return {"id": repo.save_document(doc, doc_id), "message": "Құжат сақталды."}
        if action == "status":
            if data.get("status") not in STATUSES:
                raise HttpError(400, "Мәртебе дұрыс емес.")
            repo.set_status(doc_id, data["status"])
            return {"message": "Мәртебе өзгертілді."}
        if action == "delete":
            repo.delete_document(doc_id)
            return {"message": "Құжат жойылды."}
        if action == "link":
            repo.link_student(doc_id, int(data["student_id"]), (data.get("note") or "").strip())
            return {"message": "Білім алушы қосылды."}
        if action == "unlink":
            repo.unlink_student(doc_id, int(data["student_id"]))
            return {"message": "Байланыс жойылды."}
        if parts == ["backup"]:
            return {"message": "Сақтық көшірме жасалды: backups/" + repo.backup()}
        if parts == ["reports", "run"]:
            return self.run_report(repo, data)
        raise HttpError(404, "Мұндай әрекет жоқ.")

    def run_report(self, repo, data):
        """Есеп базаға тек оқу режимінде (mode=ro) ашылған бөлек қосылымда орындалады."""
        index = data.get("id")
        if not isinstance(index, int) or not 0 <= index < len(REPORTS):
            raise HttpError(400, "Есеп табылмады.")
        title, sql, public = REPORTS[index]
        if not (public or repo.is_admin):
            raise PermissionError("Бұл есеп тек әкімшіге ашық.")
        if repo.is_admin and data.get("sql"):     # әкімші SQL мәтінін өзгерте алады
            sql = data["sql"]
        ro = sqlite3.connect(f"file:{database.DB_PATH.as_posix()}?mode=ro", uri=True)
        database.register_kazakh(ro)
        try:
            cur = ro.execute(sql)
            rows = [list(r) for r in cur.fetchmany(300)]
            columns = [d[0] for d in cur.description] if cur.description else []
        except sqlite3.Error as error:
            raise HttpError(400, f"SQL қатесі: {error}")
        finally:
            ro.close()
        return {"columns": columns, "rows": rows}

    # ----- статикалық файлдар (web бумасы) ---------------------------------------
    def do_GET(self):
        if self.path.startswith("/api/"):
            return self.handle_api("GET")
        name = urlparse(self.path).path.lstrip("/") or "index.html"
        file = (WEB_DIR / name).resolve()
        if WEB_DIR not in file.parents or not file.is_file() or file.suffix not in FILE_TYPES:
            return self.send("Бет табылмады".encode("utf-8"), "text/plain; charset=utf-8", 404)
        self.send(file.read_bytes(), FILE_TYPES[file.suffix])

    def do_POST(self):
        self.handle_api("POST")


def main():
    database.build_database()                     # база жоқ болса, құрылады
    port = PORT
    while True:
        try:
            server = ThreadingHTTPServer((HOST, port), Handler)
            break
        except OSError:                           # порт бос емес болса, келесісі алынады
            port += 1
    url = f"http://{HOST}:{port}/"
    print("EduDocs веб-қосымшасы іске қосылды:", url)
    print("Кіру: admin / Admin2026 (әкімші) немесе qonaq / Qonaq2026 (қонақ)")
    print("Тоқтату үшін PyCharm-дағы қызыл Stop батырмасын басыңыз (немесе Ctrl+C).")
    if "--no-browser" not in sys.argv:
        threading.Timer(1.0, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
