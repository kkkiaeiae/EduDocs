// EduDocs – браузерде жұмыс істейтін демо нұсқа.
// app.py серверінің /api/... сұраныстарын браузердің ішінде орындайды:
// edudocs.db файлы sql.js (SQLite → WebAssembly) арқылы ашылады, сұратымдар repository.py-дағыдай.
// Өзгерістер тек жадта сақталады: бетті жаңартқанда база бастапқы күйіне оралады.
"use strict";

(function () {
  const STATUSES = ["жоба", "келісуде", "бекітілді", "мұрағатта"];
  const PUBLIC = ["бекітілді", "мұрағатта"];
  const KZ = "аәбвгғдеёжзийкқлмнңоөпрстуұүфхһцчшщъыіьэюя";
  const KZ_ORDER = new Map([...KZ].map((c, i) => [c, i]));

  // ---- база ----------------------------------------------------------------
  const ready = (async () => {
    const SQL = await initSqlJs({ locateFile: (f) => "vendor/" + f });
    const buf = await (await fetch("edudocs.db")).arrayBuffer();
    const db = new SQL.Database(new Uint8Array(buf));
    db.run("PRAGMA foreign_keys = ON");
    db.create_function("kz_lower", (s) => (typeof s === "string" ? s.toLowerCase() : s));
    // KAZAKH салыстыру ережесінің орнына: әріптерді әліпбидегі реттік нөмірге айналдыратын кілт
    db.create_function("kz_key", (s) => [...String(s ?? "").toLowerCase()]
      .map((c) => (KZ_ORDER.has(c) ? String.fromCharCode(0x100 + KZ_ORDER.get(c)) : c)).join(""));
    return db;
  })();

  const kazakh = (sql) => sql.replace(/([\w.]+)\s+COLLATE\s+KAZAKH/gi, "kz_key($1)");

  function query(db, sql, params) {
    const st = db.prepare(kazakh(sql));
    try {
      if (params) st.bind(params);
      const rows = [];
      while (st.step()) rows.push(st.getAsObject());
      return rows;
    } finally { st.free(); }
  }
  const run = (db, sql, params) => db.run(kazakh(sql), params || []);

  // ---- сессия (тек осы қойындыда) ------------------------------------------
  let user = null;
  try { user = JSON.parse(sessionStorage.getItem("edudocs-user")) || null; } catch (e) { user = null; }
  const saveUser = () => { try { sessionStorage.setItem("edudocs-user", JSON.stringify(user)); } catch (e) { /* жоқ */ } };

  class HttpError extends Error { constructor(status, msg) { super(msg); this.status = status; } }
  const isAdmin = () => user && user.role === "admin";
  const requireAdmin = () => { if (!isAdmin()) throw new HttpError(403, "Бұл әрекет тек әкімшіге рұқсат етілген."); };

  // ---- құпиясөзді тексеру: auth.py-дағыдай PBKDF2-HMAC-SHA256 --------------
  async function verify(password, stored) {
    const [, iterations, salt, expected] = String(stored).split("$");
    const enc = new TextEncoder();
    const key = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
    const bits = await crypto.subtle.deriveBits(
      { name: "PBKDF2", hash: "SHA-256", salt: enc.encode(salt), iterations: Number(iterations) }, key, 256);
    const hex = [...new Uint8Array(bits)].map((b) => b.toString(16).padStart(2, "0")).join("");
    return hex === expected;
  }

  // ---- repository.py әдістері -------------------------------------------------
  const WHERE = ` WHERE (:q = '' OR kz_lower(title) LIKE '%' || kz_lower(:q) || '%'
                    OR kz_lower(reg_number) LIKE '%' || kz_lower(:q) || '%')
                  AND (:category = '' OR category = :category)
                  AND (:type = '' OR type_code = :type)
                  AND (:year = '' OR academic_year = :year)
                  AND (:dep = '' OR department = :dep)
                  AND (:public = 0 OR status IN ('бекітілді', 'мұрағатта'))`;
  const params = (p) => ({ ":q": (p.q || "").trim(), ":category": p.category || "", ":type": p.type || "",
    ":year": p.year || "", ":dep": p.dep || "", ":status": p.status || "", ":public": isAdmin() ? 0 : 1 });
  const registry = (db, p) => query(db, "SELECT id, reg_number, doc_date, doc_type, category, title, department, author, status " +
    "FROM v_registry" + WHERE + " AND (:status = '' OR status = :status) ORDER BY doc_date DESC, reg_number DESC", params(p));

  function lookups(db) {
    const data = {
      types: query(db, "SELECT id, code, name, category FROM document_types ORDER BY code"),
      departments: query(db, "SELECT id, name, short_name FROM departments ORDER BY id"),
      years: query(db, "SELECT DISTINCT academic_year FROM documents ORDER BY academic_year DESC").map((r) => r.academic_year),
      categories: query(db, "SELECT DISTINCT category FROM document_types ORDER BY category COLLATE KAZAKH").map((r) => r.category),
      statuses: isAdmin() ? STATUSES : PUBLIC,
    };
    if (isAdmin()) {
      data.students = query(db, "SELECT id, record_book, full_name, group_name FROM students ORDER BY full_name COLLATE KAZAKH");
      data.groups = query(db, "SELECT DISTINCT group_name FROM students ORDER BY group_name").map((r) => r.group_name);
    }
    return data;
  }

  function dashboard(db) {
    const pub = isAdmin() ? 0 : 1;
    const cond = "WHERE (? = 0 OR status IN ('бекітілді', 'мұрағатта'))";
    const data = {
      statuses: Object.fromEntries(query(db, `SELECT status, COUNT(*) AS n FROM documents ${cond} GROUP BY status`, [pub]).map((r) => [r.status, r.n])),
      categories: query(db, `SELECT category AS name, COUNT(*) AS n FROM v_registry ${cond} GROUP BY category ORDER BY n DESC`, [pub]),
      departments: query(db, `SELECT department AS name, COUNT(*) AS n FROM v_registry ${cond} GROUP BY department ORDER BY n DESC`, [pub]),
    };
    if (isAdmin()) {
      data.pending = query(db, "SELECT id, reg_number, doc_type, status, CAST(julianday('now') - julianday(doc_date) AS INTEGER) AS days " +
        "FROM v_registry WHERE status IN ('жоба', 'келісуде') ORDER BY doc_date");
    } else {
      data.latest = query(db, "SELECT id, reg_number, doc_type, doc_date FROM v_registry WHERE status = 'бекітілді' ORDER BY doc_date DESC LIMIT 8");
    }
    return data;
  }

  function documentById(db, id) {
    const rows = query(db, "SELECT d.*, t.name AS doc_type, t.category, t.retention_years, dep.name AS department " +
      "FROM documents d JOIN document_types t ON t.id = d.type_id JOIN departments dep ON dep.id = d.department_id " +
      "WHERE d.id = ? AND (? = 1 OR d.status IN ('бекітілді', 'мұрағатта'))", [id, isAdmin() ? 1 : 0]);
    if (!rows.length) throw new HttpError(404, "Құжат табылмады.");
    return rows[0];
  }

  function nextNumber(db, typeId, year) {
    const code = query(db, "SELECT code FROM document_types WHERE id = ?", [typeId])[0];
    if (!code) return "";
    const prefix = `${code.code}-${year}/`;
    const last = query(db, "SELECT MAX(CAST(substr(reg_number, ?) AS INTEGER)) AS m FROM documents WHERE reg_number LIKE ?",
      [prefix.length + 1, prefix + "%"])[0].m;
    return prefix + String((last || 0) + 1).padStart(3, "0");
  }

  const FIELDS = ["reg_number", "type_id", "title", "doc_date", "academic_year", "department_id", "author", "status", "pages"];
  function saveDocument(db, data, id) {
    requireAdmin();
    const doc = {};
    FIELDS.forEach((f) => (doc[f] = data[f]));
    ["type_id", "department_id", "pages"].forEach((f) => (doc[f] = /^\d+$/.test(String(doc[f] ?? "")) ? Number(doc[f]) : null));
    ["reg_number", "title", "author", "doc_date", "academic_year"].forEach((f) => (doc[f] = String(doc[f] ?? "").trim() || null));
    doc.status = doc.status || "жоба";
    const missing = [["reg_number", "тіркеу нөмірі"], ["type_id", "құжат түрі"], ["title", "атауы"], ["doc_date", "күні"],
      ["academic_year", "оқу жылы"], ["department_id", "бөлімше"]].filter(([f]) => !doc[f]).map(([, n]) => n);
    if (missing.length) throw new HttpError(400, "Міндетті өрістер толтырылмаған: " + missing.join(", "));
    const values = FIELDS.map((f) => doc[f]);
    if (id == null) {
      run(db, `INSERT INTO documents (${FIELDS.join(", ")}) VALUES (${FIELDS.map(() => "?").join(", ")})`, values);
      return query(db, "SELECT last_insert_rowid() AS id")[0].id;
    }
    run(db, `UPDATE documents SET ${FIELDS.map((f) => f + " = ?").join(", ")} WHERE id = ?`, [...values, id]);
    return id;
  }

  let REPORTS = null;
  async function reports() {
    if (!REPORTS) REPORTS = await (await fetch("reports.json")).json();
    return REPORTS;
  }

  function runReport(db, sql) {
    // есеп «тек оқу» режимінде: savepoint ішінде орындалып, өзгерістер кері қайтарылады
    db.run("SAVEPOINT report");
    try {
      const res = db.exec(kazakh(sql));
      const last = res.length ? res[res.length - 1] : { columns: [], values: [] };
      return { columns: last.columns, rows: last.values.slice(0, 300) };
    } catch (e) {
      throw new HttpError(400, "SQL қатесі: " + e.message);
    } finally {
      db.run("ROLLBACK TO report");
      db.run("RELEASE report");
    }
  }

  function download(name, blob) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  function csv(db, p) {
    const q = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const lines = [["Тіркеу №", "Күні", "Түрі", "Атауы", "Бөлімше", "Жауапты", "Мәртебесі"].map(q).join(";")];
    registry(db, p).forEach((r) => lines.push([r.reg_number, r.doc_date, r.doc_type, r.title, r.department, r.author, r.status].map(q).join(";")));
    download("edudocs.csv", new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" }));
  }

  // ---- маршруттар (app.py-дағыдай) ---------------------------------------------
  async function handle(method, url, body) {
    const db = await ready;
    const path = url.pathname.replace(/^.*\/api\//, "/api/");
    const p = Object.fromEntries(url.searchParams.entries());
    if (path === "/api/login" && method === "POST") {
      const row = query(db, "SELECT id, username, password_hash, role, full_name FROM users WHERE username = ?",
        [String(body.username || "").trim()])[0];
      if (!row || !(await verify(body.password || "", row.password_hash))) throw new HttpError(401, "Логин немесе құпиясөз қате.");
      user = { id: row.id, username: row.username, role: row.role, full_name: row.full_name };
      saveUser();
      return { user };
    }
    if (path === "/api/me") return { user };
    if (!user) throw new HttpError(401, "Алдымен жүйеге кіріңіз.");
    if (path === "/api/logout") { user = null; saveUser(); return { user: null }; }
    const parts = path.split("/").filter(Boolean).slice(1);

    if (method === "GET") {
      if (parts[0] === "lookups") return lookups(db);
      if (parts[0] === "dashboard") return dashboard(db);
      if (parts.length === 1 && parts[0] === "documents") {
        const counts = Object.fromEntries(query(db, "SELECT status, COUNT(*) AS n FROM v_registry" + WHERE + " GROUP BY status", params(p))
          .map((r) => [r.status, r.n]));
        return { rows: registry(db, p), counts };
      }
      if (parts[0] === "documents" && parts.length === 2) {
        const id = Number(parts[1]);
        const data = { document: documentById(db, id) };
        if (isAdmin()) data.students = query(db, "SELECT s.id, s.record_book, s.full_name, s.group_name, ds.note " +
          "FROM document_students ds JOIN students s ON s.id = ds.student_id WHERE ds.document_id = ? ORDER BY s.full_name COLLATE KAZAKH", [id]);
        return data;
      }
      if (parts[0] === "next-number") return { reg_number: nextNumber(db, p.type, (p.year || "").slice(0, 4)) };
      if (parts[0] === "students" && parts.length === 1) {
        requireAdmin();
        return query(db, "SELECT s.id, s.record_book, s.full_name, s.group_name, s.course, s.email, COUNT(ds.document_id) AS documents " +
          "FROM students s LEFT JOIN document_students ds ON ds.student_id = s.id " +
          "WHERE (:q = '' OR kz_lower(s.full_name) LIKE '%' || kz_lower(:q) || '%' OR s.record_book LIKE :q || '%') " +
          "AND (:group = '' OR s.group_name = :group) GROUP BY s.id ORDER BY s.full_name COLLATE KAZAKH",
        { ":q": (p.q || "").trim(), ":group": p.group || "" });
      }
      if (parts[0] === "students" && parts.length === 2) {
        requireAdmin();
        return query(db, "SELECT d.id, d.reg_number, d.doc_date, t.name AS doc_type, d.status, ds.note " +
          "FROM document_students ds JOIN documents d ON d.id = ds.document_id JOIN document_types t ON t.id = d.type_id " +
          "WHERE ds.student_id = ? ORDER BY d.doc_date DESC", [Number(parts[1])]);
      }
      if (parts[0] === "reports") return (await reports()).map((r, i) => ({ id: i, title: r.title, sql: r.sql, public: r.public }))
        .filter((r) => r.public || isAdmin());
      throw new HttpError(404, "Мұндай бет жоқ.");
    }

    // POST
    const id = /^\d+$/.test(parts[1] || "") ? Number(parts[1]) : null;
    const action = parts[2] || "";
    if (parts[0] === "documents" && (action === "" || action === "save")) {
      return { id: saveDocument(db, body, id), message: "Құжат сақталды." };
    }
    if (action === "status") {
      requireAdmin();
      if (!STATUSES.includes(body.status)) throw new HttpError(400, "Мәртебе дұрыс емес.");
      run(db, "UPDATE documents SET status = ? WHERE id = ?", [body.status, id]);
      return { message: "Мәртебе өзгертілді." };
    }
    if (action === "delete") { requireAdmin(); run(db, "DELETE FROM documents WHERE id = ?", [id]); return { message: "Құжат жойылды." }; }
    if (action === "link") {
      requireAdmin();
      run(db, "INSERT INTO document_students VALUES (?, ?, ?)", [id, Number(body.student_id), (body.note || "").trim() || null]);
      return { message: "Білім алушы қосылды." };
    }
    if (action === "unlink") {
      requireAdmin();
      run(db, "DELETE FROM document_students WHERE document_id = ? AND student_id = ?", [id, Number(body.student_id)]);
      return { message: "Байланыс жойылды." };
    }
    if (parts[0] === "backup") {
      requireAdmin();
      download("edudocs_backup.db", new Blob([db.export()], { type: "application/x-sqlite3" }));
      db.run("PRAGMA foreign_keys = ON");          // export() қосылымды қайта ашады
      return { message: "Сақтық көшірме жүктелді: edudocs_backup.db" };
    }
    if (parts[0] === "reports" && parts[1] === "run") {
      const list = await reports();
      const r = list[body.id];
      if (!r) throw new HttpError(400, "Есеп табылмады.");
      if (!(r.public || isAdmin())) throw new HttpError(403, "Бұл есеп тек әкімшіге ашық.");
      return runReport(db, isAdmin() && body.sql ? body.sql : r.sql);
    }
    throw new HttpError(404, "Мұндай әрекет жоқ.");
  }

  // ---- fetch-ті ұстап алу ----------------------------------------------------
  const realFetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const url = new URL(typeof input === "string" ? input : input.url, location.href);
    if (!url.pathname.includes("/api/")) return realFetch(input, init);
    const method = (init && init.method) || "GET";
    let body = {};
    try { body = init && init.body ? JSON.parse(init.body) : {}; } catch (e) { body = {}; }
    const json = (data, status) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
    try {
      return json(await handle(method, url, body), 200);
    } catch (e) {
      if (e instanceof HttpError) return json({ error: e.message }, e.status);
      return json({ error: "Деректер базасының қатесі: " + e.message }, 409);   // шектеулер мен триггер хабарлары
    }
  };

  // CSV сілтемесі серверсіз: файлды браузердің өзі жасайды
  document.addEventListener("click", async (e) => {
    const a = e.target.closest('a[href*="/api/export.csv"]');
    if (!a) return;
    e.preventDefault();
    const url = new URL(a.getAttribute("href"), location.href);
    csv(await ready, Object.fromEntries(url.searchParams.entries()));
  });
})();
