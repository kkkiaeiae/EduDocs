// EduDocs — браузердегі интерфейс. Деректерді app.py серверінен JSON түрінде алады.
"use strict";

const state = { user: null, page: "dashboard", lookups: null, sort: {} };

// ---------------------------------------------------------------------------
//  Белгішелер (SVG) және беттер тізімі
// ---------------------------------------------------------------------------
const PAGES = [
  { id: "dashboard", title: "Басты бет" },
  { id: "registry", title: "Құжаттар тізілімі" },
  { id: "students", title: "Білім алушылар", admin: true },
  { id: "reports", title: "SQL есептер" },
];

// ---------------------------------------------------------------------------
//  Көмекші функциялар
// ---------------------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const esc = (v) => String(v ?? "—").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const isAdmin = () => state.user && state.user.role === "admin";
const statusTag = (s) => `<span class="st st-${esc(s)}">${esc(s)}</span>`;
const query = (obj) => new URLSearchParams(Object.entries(obj).filter(([, v]) => v)).toString();

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (res.status === 401 && state.user) { state.user = null; showLogin(); }
  if (!res.ok) throw new Error(data.error || `Қате (${res.status})`);
  return data;
}

function toast(message, error = false) {
  const t = $("#toast");
  t.textContent = message;
  t.className = "toast" + (error ? " error" : "");
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.hidden = true), 3500);
}

// Сұрыптау: сандар сан ретінде, мәтін қазақ әліпбиі бойынша салыстырылады
const collator = new Intl.Collator("kk", { numeric: true });
function compare(a, b) {
  if (a == null || b == null) return (a == null) - (b == null);
  if (typeof a === "number" && typeof b === "number") return a - b;
  return collator.compare(String(a), String(b));
}

// Кестені салу. Баған тақырыбын басқанда сұрыпталады: ▲ өсу, ▼ кему
function table(id, columns, rows, rowId) {
  const sort = state.sort[id];
  const data = rows.slice();
  if (sort) data.sort((x, y) => compare(x[sort.key], y[sort.key]) * (sort.asc ? 1 : -1));
  const head = columns.map((c) => {
    if (c.nosort) return `<th class="${c.cls || ""}">${c.label}</th>`;
    const arrow = sort && sort.key === c.key ? `<span class="arrow">${sort.asc ? "▲" : "▼"}</span>` : "";
    return `<th class="sortable ${c.cls || ""}" data-table="${id}" data-key="${c.key}">${c.label}${arrow}</th>`;
  }).join("");
  const body = data.length ? data.map((r) =>
    `<tr${rowId ? ` class="clickable" data-id="${r[rowId]}"` : ""}>` + columns.map((c) =>
      `<td class="${c.cls || ""}">${c.render ? c.render(r) : esc(r[c.key])}</td>`).join("") + "</tr>").join("")
    : `<tr><td class="empty" colspan="${columns.length}">Жазба табылмады</td></tr>`;
  return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

let redraw = () => {};
document.addEventListener("click", (e) => {
  const th = e.target.closest("th.sortable");
  if (!th) return;
  const { table: id, key } = th.dataset;
  const cur = state.sort[id];
  state.sort[id] = { key, asc: !(cur && cur.key === key && cur.asc) };
  redraw();
});

function pageHead(title, text, actions = "") {
  return `<div class="page-head"><div><h1>${title}</h1><p>${text}</p></div>
    <div class="actions">${actions}</div></div>`;
}

// ---------------------------------------------------------------------------
//  Кіру және шығу
// ---------------------------------------------------------------------------
function showLogin() {
  $("#shell").hidden = true;
  $("#login").hidden = false;
  $("#password").value = "";
  $("#username").focus();
}

$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#loginError").hidden = true;
  try {
    const data = await api("/api/login", { username: $("#username").value, password: $("#password").value });
    state.user = data.user;
    startApp();
  } catch (error) {
    $("#loginError").textContent = error.message;
    $("#loginError").hidden = false;
  }
});

$("#logout").addEventListener("click", async () => {
  await api("/api/logout", {});
  state.user = null;
  showLogin();
});

async function startApp() {
  $("#login").hidden = true;
  $("#shell").hidden = false;
  $("#roleBadge").textContent = isAdmin() ? "әкімші" : "қонақ";
  $("#userName").textContent = state.user.full_name || state.user.username;
  state.lookups = await api("/api/lookups");
  const pages = PAGES.filter((p) => !p.admin || isAdmin());
  $("#nav").innerHTML = pages.map((p) =>
    `<button class="tab" type="button" data-page="${p.id}">${p.title}</button>`).join("");
  go(pages.some((p) => p.id === state.page) ? state.page : "dashboard");
}

$("#nav").addEventListener("click", (e) => {
  const link = e.target.closest(".tab");
  if (link) go(link.dataset.page);
});

const RENDER = {};
function go(page) {
  state.page = page;
  $("#crumb").textContent = "Пайдаланушы: " + state.user.username;
  document.querySelectorAll(".tab").forEach((l) => l.classList.toggle("active", l.dataset.page === page));
  RENDER[page]().catch((error) => ($("#content").innerHTML = `<div class="empty">${esc(error.message)}</div>`));
}

// ---------------------------------------------------------------------------
//  1. Басты бет
// ---------------------------------------------------------------------------
RENDER.dashboard = async () => {
  const d = await api("/api/dashboard");
  const s = d.statuses;
  const total = Object.values(s).reduce((a, b) => a + b, 0);
  const names = isAdmin() ? ["жоба", "келісуде", "бекітілді", "мұрағатта"] : ["бекітілді", "мұрағатта"];
  const summary = `<table class="summary"><thead><tr><th>Мәртебе</th><th class="num">Құжат саны</th></tr></thead><tbody>
    ${names.map((n) => `<tr><td>${statusTag(n)}</td><td class="num">${s[n] || 0}</td></tr>`).join("")}
    <tr><td><b>Барлығы</b></td><td class="num">${total}</td></tr></tbody></table>`;
  const bars = (list) => {
    const max = Math.max(1, ...list.map((x) => x.n));
    return `<table class="bars"><tbody>${list.map((x) => `<tr><td class="label">${esc(x.name)}</td>
      <td><div class="bar" style="width:${(100 * x.n) / max}%"></div></td><td class="num">${x.n}</td></tr>`).join("")}</tbody></table>`;
  };
  const side = isAdmin()
    ? `<h3>Бекітілмеген құжаттар (жоба, келісуде)</h3>` +
      table("pending", [{ key: "reg_number", label: "Тіркеу №", cls: "mono" }, { key: "doc_type", label: "Түрі" },
        { key: "status", label: "Мәртебесі", render: (r) => statusTag(r.status) },
        { key: "days", label: "Күтуде, күн", cls: "num" }], d.pending)
    : `<h3>Соңғы бекітілген құжаттар</h3>` +
      table("latest", [{ key: "reg_number", label: "Тіркеу №", cls: "mono" }, { key: "doc_type", label: "Түрі" },
        { key: "doc_date", label: "Күні", cls: "nowrap" }], d.latest);
  $("#content").innerHTML = pageHead("Басты бет",
      isAdmin() ? "Тіркелген құжаттар туралы жиынтық мәлімет."
                : "Қонақ режимі: тек бекітілген және мұрағаттағы құжаттар көрсетіледі.",
      isAdmin() ? `<button class="button" id="backup">Сақтық көшірме жасау</button>` : "") +
    `<div class="cols wide-right"><div class="stack">
       <div class="box"><h3>Мәртебелер бойынша</h3>${summary}</div>
       <div class="box"><h3>Санаттар бойынша</h3><div class="box-body">${bars(d.categories)}</div></div>
       <div class="box"><h3>Бөлімшелер бойынша</h3><div class="box-body">${bars(d.departments)}</div></div>
     </div><div class="box">${side}</div></div>`;
  if (isAdmin()) $("#backup").onclick = async () => toast((await api("/api/backup", {})).message);
  redraw = RENDER.dashboard;
};

// ---------------------------------------------------------------------------
//  2. Құжаттар тізілімі: сол жақта сүзгілер, оң жақта кесте
// ---------------------------------------------------------------------------
const filters = { q: "", category: "", type: "", year: "", dep: "", status: "" };
let registry = { rows: [], counts: {} };

RENDER.registry = async () => {
  registry = await api("/api/documents?" + query(filters));
  drawRegistry();
  redraw = drawRegistry;
};

function drawRegistry() {
  const L = state.lookups;
  const types = L.types.filter((t) => !filters.category || t.category === filters.category);
  const select = (key, all, items) => `<select data-filter="${key}"><option value="">${all}</option>${items.map(([v, t]) =>
    `<option value="${esc(v)}"${filters[key] === v ? " selected" : ""}>${esc(t)}</option>`).join("")}</select>`;
  const total = Object.values(registry.counts).reduce((a, b) => a + b, 0);
  const statuses = [["", "барлығы", total], ...L.statuses.map((s) => [s, s, registry.counts[s] || 0])].map(([v, t, n]) =>
    `<button type="button" class="${filters.status === v ? "on" : ""}" data-status="${v}">${t} (${n})</button>`).join("");
  const cols = [
    { key: "reg_number", label: "Тіркеу №", cls: "mono" },
    { key: "doc_date", label: "Күні", cls: "nowrap" },
    { key: "doc_type", label: "Түрі" },
    { key: "title", label: "Атауы", render: (r) => `${esc(r.title)}<span class="sub">${esc(r.author)}, ${esc(r.department)}</span>` },
    { key: "status", label: "Мәртебесі", render: (r) => statusTag(r.status) },
  ];
  if (isAdmin()) cols.push({ key: "_", label: "Әрекет", nosort: true, render: (r) => `<span class="row-actions">
    <button data-act="edit" data-id="${r.id}">өзгерту</button><button data-act="status" data-id="${r.id}">мәртебе</button><button class="del" data-act="delete" data-id="${r.id}">жою</button></span>` });
  $("#content").innerHTML = pageHead("Құжаттар тізілімі",
      "Сүзгілер SQL сұратымының WHERE шартына айналады. Сұрыптау үшін баған тақырыбын басыңыз.",
      `<a class="button" href="/api/export.csv?${query(filters)}">CSV файлына сақтау</a>` +
      (isAdmin() ? `<button class="button primary" id="newDoc">Жаңа құжат</button>` : "")) +
    `<div class="search-form">
       <div><label>Санат</label><div class="cats">${["", ...L.categories].map((c) => `<label>
         <input type="radio" name="cat" value="${c}"${filters.category === c ? " checked" : ""}>${c || "барлығы"}</label>`).join("")}</div></div>
       <div><label>Құжат түрі</label>${select("type", "барлығы", types.map((t) => [t.code, t.name]))}</div>
       <div><label>Оқу жылы</label>${select("year", "барлығы", L.years.map((y) => [y, y]))}</div>
       <div><label>Бөлімше</label>${select("dep", "барлығы", L.departments.map((d) => [d.short_name, d.name]))}</div>
       <div class="q"><label>Атауы немесе тіркеу нөмірі</label><input id="q" value="${esc(filters.q === "" ? "" : filters.q)}"></div>
       <div class="buttons"><button class="button" type="button" id="reset">Тазарту</button></div>
     </div>
     <div class="statuses">Мәртебе: ${statuses}<span class="total">Табылды: ${registry.rows.length}</span></div>
     <div class="catalog">${table("registry", cols, registry.rows, "id")}</div>`;

  const reload = () => RENDER.registry();
  document.querySelectorAll("input[name=cat]").forEach((r) => (r.onchange = () => { filters.category = r.value; filters.type = ""; reload(); }));
  document.querySelectorAll("[data-filter]").forEach((s) => (s.onchange = () => { filters[s.dataset.filter] = s.value; reload(); }));
  document.querySelectorAll("[data-status]").forEach((b) => (b.onclick = () => { filters.status = b.dataset.status; reload(); }));
  $("#reset").onclick = () => { Object.keys(filters).forEach((k) => (filters[k] = "")); reload(); };
  const q = $("#q");
  q.oninput = () => { clearTimeout(q.timer); q.timer = setTimeout(() => { filters.q = q.value; reload().then(() => {
    const box = $("#q"); box.focus(); box.setSelectionRange(box.value.length, box.value.length); }); }, 350); };
  if (isAdmin()) $("#newDoc").onclick = () => documentForm();
  document.querySelector(".catalog tbody").onclick = (e) => {
    const btn = e.target.closest("[data-act]");
    if (btn) {
      const id = Number(btn.dataset.id);
      if (btn.dataset.act === "edit") documentForm(id);
      if (btn.dataset.act === "status") statusForm(id);
      if (btn.dataset.act === "delete") deleteDocument(id);
      return;
    }
    const row = e.target.closest("tr[data-id]");
    if (row) documentCard(Number(row.dataset.id));
  };
}

// ---------------------------------------------------------------------------
//  Диалог терезелері: құжат картасы, форма, мәртебе, жою
// ---------------------------------------------------------------------------
const dialog = $("#dialog");
function openDialog(caption, title, body) {
  dialog.innerHTML = `<div class="dlg-head"><h2>${caption}</h2>
    <button class="x" type="button" data-close aria-label="Жабу">×</button></div>
    <div class="dlg-body"><div class="dlg-title">${title}</div>${body}</div>`;
  dialog.querySelectorAll("[data-close]").forEach((b) => (b.onclick = () => dialog.close()));
  if (!dialog.open) dialog.showModal();
}

async function documentCard(id) {
  const d = await api(`/api/documents/${id}`);
  const doc = d.document;
  let students = "";
  if (isAdmin()) {
    students = `<div class="section-title">Құжатқа қатысты білім алушылар (document_students)</div>` +
      table("cardStudents", [{ key: "record_book", label: "ID", cls: "mono" }, { key: "full_name", label: "Аты-жөні" },
        { key: "group_name", label: "Тобы", cls: "nowrap" }, { key: "note", label: "Ескерту" },
        { key: "_", label: "", nosort: true, render: (r) => `<button class="link" data-unlink="${r.id}">алып тастау</button>` }],
        d.students) +
      `<div class="link-row"><select id="linkStudent"><option value="">білім алушыны таңдаңыз</option>${state.lookups.students.map((s) =>
        `<option value="${s.id}">${esc(s.full_name)} (${esc(s.group_name)})</option>`).join("")}</select>
        <input id="linkNote" placeholder="ескерту"><button class="button" id="linkBtn">Қосу</button></div>`;
  }
  openDialog("Құжат картасы: " + esc(doc.reg_number), esc(doc.title), `${statusTag(doc.status)}
    <dl class="meta"><dt>Түрі</dt><dd>${esc(doc.doc_type)} (${esc(doc.category)})</dd>
      <dt>Күні</dt><dd>${esc(doc.doc_date)}</dd><dt>Оқу жылы</dt><dd>${esc(doc.academic_year)}</dd>
      <dt>Бөлімше</dt><dd>${esc(doc.department)}</dd><dt>Жауапты</dt><dd>${esc(doc.author)}</dd>
      <dt>Беттер саны</dt><dd>${esc(doc.pages)}</dd><dt>Сақтау мерзімі</dt><dd>${esc(doc.retention_years)} жыл</dd></dl>
    ${students}<div class="dlg-actions"><button class="button primary" data-close>Жабу</button></div>`);
  if (!isAdmin()) return;
  $("#linkBtn").onclick = async () => {
    if (!$("#linkStudent").value) return;
    try {
      toast((await api(`/api/documents/${id}/link`, { student_id: Number($("#linkStudent").value), note: $("#linkNote").value })).message);
      documentCard(id);
    } catch (error) { toast(error.message, true); }
  };
  dialog.querySelectorAll("[data-unlink]").forEach((b) => (b.onclick = async () => {
    toast((await api(`/api/documents/${id}/unlink`, { student_id: Number(b.dataset.unlink) })).message);
    documentCard(id);
  }));
}

async function documentForm(id) {
  const L = state.lookups;
  const doc = id ? (await api(`/api/documents/${id}`)).document
    : { status: "жоба", doc_date: new Date().toISOString().slice(0, 10), academic_year: L.years[0] };
  const opt = (items, value) => items.map(([v, t]) => `<option value="${esc(v)}"${String(v) === String(value) ? " selected" : ""}>${esc(t)}</option>`).join("");
  const field = (label, html, full) => `<div class="field${full ? " full" : ""}"><label>${label}</label>${html}</div>`;
  openDialog(id ? "Құжатты өзгерту" : "Құжатты тіркеу", id ? esc(doc.reg_number) : "Жаңа құжат", `<form id="docForm"><div class="form-grid">
    ${field("Құжат түрі *", `<select name="type_id"><option value="">—</option>${opt(L.types.map((t) => [t.id, `${t.code} — ${t.name}`]), doc.type_id)}</select>`)}
    ${field("Тіркеу нөмірі *", `<input name="reg_number" value="${esc(doc.reg_number ?? "")}">`)}
    ${field("Атауы *", `<input name="title" value="${esc(doc.title ?? "")}">`, true)}
    ${field("Құжат күні *", `<input name="doc_date" type="date" value="${esc(doc.doc_date)}">`)}
    ${field("Оқу жылы *", `<select name="academic_year">${opt(["2027-2028", ...L.years].map((y) => [y, y]), doc.academic_year)}</select>`)}
    ${field("Бөлімше *", `<select name="department_id"><option value="">—</option>${opt(L.departments.map((d) => [d.id, d.name]), doc.department_id)}</select>`)}
    ${field("Жауапты қызметкер", `<input name="author" value="${esc(doc.author ?? "")}">`)}
    ${field("Мәртебесі", `<select name="status">${opt(L.statuses.map((s) => [s, s]), doc.status)}</select>`)}
    ${field("Беттер саны", `<input name="pages" type="number" min="1" value="${esc(doc.pages ?? "")}">`)}
    </div><div class="dlg-actions"><button type="button" class="button" data-close>Болдырмау</button>
    <button class="button primary">Сақтау</button></div></form>`);
  const form = $("#docForm");
  form.type_id.onchange = async () => {        // келесі тіркеу нөмірі MAX() арқылы ұсынылады
    if (id || !form.type_id.value) return;
    form.reg_number.value = (await api(`/api/next-number?${query({ type: form.type_id.value, year: form.doc_date.value })}`)).reg_number;
  };
  form.onsubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await api(id ? `/api/documents/${id}/save` : "/api/documents", Object.fromEntries(new FormData(form)));
      dialog.close();
      toast(res.message);
      RENDER.registry();
    } catch (error) { toast(error.message, true); }
  };
}

async function statusForm(id) {
  const doc = (await api(`/api/documents/${id}`)).document;
  openDialog("Мәртебені өзгерту", esc(doc.reg_number), `<p class="muted">${esc(doc.title)}</p>
    <div class="field" style="margin-top:14px"><label>Жаңа мәртебе</label><select id="newStatus">${state.lookups.statuses.map((s) =>
      `<option${s === doc.status ? " selected" : ""}>${s}</option>`).join("")}</select></div>
    <div class="dlg-actions"><button class="button" data-close>Болдырмау</button>
    <button class="button primary" id="saveStatus">Сақтау</button></div>`);
  $("#saveStatus").onclick = async () => {
    toast((await api(`/api/documents/${id}/status`, { status: $("#newStatus").value })).message);
    dialog.close();
    RENDER.registry();
  };
}

async function deleteDocument(id) {
  const doc = (await api(`/api/documents/${id}`)).document;
  openDialog("Құжатты жою", esc(doc.reg_number), `<p>${esc(doc.title)}</p>
    <div class="note" style="margin-top:12px">Бекітілген немесе мұрағаттағы құжатты
    trg_protect_approved триггері жоюға жібермейді.</div>
    <div class="dlg-actions"><button class="button" data-close>Болдырмау</button>
    <button class="button danger" id="confirmDelete">Жою</button></div>`);
  $("#confirmDelete").onclick = async () => {
    try {
      toast((await api(`/api/documents/${id}/delete`, {})).message);
      dialog.close();
      RENDER.registry();
    } catch (error) { toast(error.message, true); }
  };
}

// ---------------------------------------------------------------------------
//  3. Білім алушылар (тек әкімші)
// ---------------------------------------------------------------------------
const studentFilter = { q: "", group: "" };
let selectedStudent = null;

RENDER.students = async () => {
  const list = await api("/api/students?" + query(studentFilter));
  const docs = selectedStudent ? await api(`/api/students/${selectedStudent}`) : null;
  const person = list.find((s) => s.id === selectedStudent);
  const draw = () => {
    $("#content").innerHTML = pageHead("Білім алушылар", "Білім алушыны таңдасаңыз, оған қатысты құжаттар шығады.") +
      `<div class="cols split"><section class="box"><div class="toolbar">
        <input id="sq" placeholder="аты-жөні немесе ID" value="${esc(studentFilter.q || "")}">
        <select id="sg"><option value="">Барлық топтар</option>${state.lookups.groups.map((g) =>
          `<option${g === studentFilter.group ? " selected" : ""}>${g}</option>`).join("")}</select>
        <span class="count-note">${list.length} білім алушы</span></div>
        ${table("students", [{ key: "record_book", label: "ID", cls: "mono" }, { key: "full_name", label: "Аты-жөні" },
          { key: "group_name", label: "Тобы", cls: "nowrap" }, { key: "course", label: "Курс", cls: "center" },
          { key: "documents", label: "Құжат", cls: "num" }], list, "id")}</section>
      <section class="box detail"><h3>Білім алушы туралы</h3><div class="box-body">${person ? `
        <h2>${esc(person.full_name)}</h2><dl class="meta"><dt>ID нөмірі</dt><dd>${esc(person.record_book)}</dd><dt>Тобы</dt><dd>${esc(person.group_name)}, ${person.course}-курс</dd>
        <dt>E-mail</dt><dd>${esc(person.email)}</dd></dl><div class="section-title">Қатысты құжаттар (document_students)</div>` +
        table("studentDocs", [{ key: "reg_number", label: "Тіркеу №", cls: "mono" }, { key: "doc_type", label: "Түрі" },
          { key: "doc_date", label: "Күні", cls: "nowrap" }, { key: "note", label: "Ескерту" }], docs)
        : `<div class="empty">Тізімнен білім алушыны таңдаңыз</div>`}</div></section></div>`;
    const sq = $("#sq");
    sq.oninput = () => { clearTimeout(sq.timer); sq.timer = setTimeout(() => { studentFilter.q = sq.value; RENDER.students().then(() => {
      const box = $("#sq"); box.focus(); box.setSelectionRange(box.value.length, box.value.length); }); }, 350); };
    $("#sg").onchange = () => { studentFilter.group = $("#sg").value; RENDER.students(); };
    document.querySelector(".split tbody").onclick = (e) => {
      const row = e.target.closest("tr[data-id]");
      if (row) { selectedStudent = Number(row.dataset.id); RENDER.students(); }
    };
    document.querySelectorAll(".split tr[data-id]").forEach((r) =>
      r.classList.toggle("selected", Number(r.dataset.id) === selectedStudent));
  };
  draw();
  redraw = draw;
};

// ---------------------------------------------------------------------------
//  4. SQL есептер: база тек оқу режимінде ашылады
// ---------------------------------------------------------------------------
let reports = [], report = null, result = null;

RENDER.reports = async () => {
  reports = await api("/api/reports");
  if (!report) report = reports[0];
  const draw = () => {
    const cols = result ? result.columns.map((c, i) => ({ key: i, label: esc(c) })) : [];
    $("#content").innerHTML = pageHead("SQL есептер",
        isAdmin() ? `${reports.length} дайын есеп. SQL мәтінін өзгертіп, қайта орындауға болады.`
                  : `${reports.length} ашық есеп. Қонақ SQL мәтінін өзгерте алмайды.`) +
      `<div class="cols split" style="grid-template-columns:minmax(0,2fr) minmax(0,3fr)"><section class="box"><h3>Дайын есептер</h3>
        <ol class="report-list">${reports.map((r, i) => `<li><button data-report="${i}" class="${r === report ? "on" : ""}">${esc(r.title)}</button></li>`).join("")}</ol></section>
       <section class="box"><h3>Сұратым мәтіні</h3><div class="box-body">
        <div class="note">Есеп базаға тек оқу режимінде (mode=ro) ашылған қосылыммен орындалады,
          сондықтан UPDATE немесе DELETE деректерді өзгерте алмайды.</div>
        <textarea class="sql" id="sql"${isAdmin() ? "" : " readonly"}>${esc(report.sql)}</textarea>
        <div style="display:flex;align-items:center;margin-top:8px"><button class="button primary" id="run">Орындау</button>
        <span class="count-note">${result ? "Нәтиже: " + result.rows.length + " жол" : ""}</span></div></div>
        ${result ? table("result", cols, result.rows) : ""}</section></div>`;
    document.querySelectorAll("[data-report]").forEach((b) => (b.onclick = () => {
      report = reports[Number(b.dataset.report)]; result = null; state.sort.result = null; draw(); run(); }));
    $("#run").onclick = run;
  };
  const run = async () => {
    try {
      result = await api("/api/reports/run", { id: report.id, sql: isAdmin() ? $("#sql").value : null });
      state.sort.result = null;
    } catch (error) { toast(error.message, true); result = null; }
    draw();
  };
  draw();
  redraw = draw;
  if (!result) run();
};

// ---------------------------------------------------------------------------
//  Іске қосу: бұрын кірген болса, бірден басты бет ашылады
// ---------------------------------------------------------------------------
(async () => {
  state.user = (await api("/api/me")).user;
  if (state.user) startApp(); else showLogin();
})();
