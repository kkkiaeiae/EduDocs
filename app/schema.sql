-- =====================================================================
--  EduDocs — мемлекеттік ЖОО-дағы оқу үдерісіне қатысты құжаттарды
--  есепке алуға арналған деректер базасы
--  ДББЖ: SQLite 3.   Кестелер саны: 6
-- =====================================================================

-- 1. Бөлімшелер: кафедралар және тіркеу офисі
CREATE TABLE departments (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,          -- толық атауы
    short_name  TEXT    NOT NULL UNIQUE           -- қысқаша атауы (ЖИТ, АЖ …)
);

-- 2. Құжат түрлері (анықтамалық)
CREATE TABLE document_types (
    id               INTEGER PRIMARY KEY,
    code             TEXT    NOT NULL UNIQUE,     -- тіркеу нөміріндегі код (СИЛ, ВЕД …)
    name             TEXT    NOT NULL,
    category         TEXT    NOT NULL
                     CHECK (category IN ('оқу-әдістемелік', 'аттестаттау',
                                         'контингент', 'нормативтік')),
    retention_years  INTEGER CHECK (retention_years > 0)   -- сақтау мерзімі, жыл
);

-- 3. Құжаттар — жүйенің негізгі кестесі (тіркеу журналы)
CREATE TABLE documents (
    id             INTEGER PRIMARY KEY,
    reg_number     TEXT    NOT NULL UNIQUE,       -- тіркеу нөмірі, мысалы СИЛ-2026/001
    type_id        INTEGER NOT NULL REFERENCES document_types(id) ON DELETE RESTRICT,
    title          TEXT    NOT NULL,
    doc_date       TEXT    NOT NULL CHECK (doc_date LIKE '____-__-__'),           -- ЖЖЖЖ-АА-КК
    academic_year  TEXT    NOT NULL CHECK (academic_year LIKE '____-____'),       -- 2026-2027
    department_id  INTEGER NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
    author         TEXT,                          -- жауапты қызметкер
    status         TEXT    NOT NULL DEFAULT 'жоба'
                   CHECK (status IN ('жоба', 'келісуде', 'бекітілді', 'мұрағатта')),
    pages          INTEGER CHECK (pages > 0)
);

-- 4. Білім алушылар
CREATE TABLE students (
    id           INTEGER PRIMARY KEY,
    record_book  TEXT    NOT NULL UNIQUE,         -- ID нөмірі
    full_name    TEXT    NOT NULL,
    group_name   TEXT    NOT NULL,                -- академиялық топ, мысалы ЖИТ-25-1
    course       INTEGER NOT NULL CHECK (course BETWEEN 1 AND 4),
    email        TEXT    UNIQUE
);

-- 5. Құжат пен білім алушы арасындағы «көпке-көп» байланыс
--    (бір бұйрықта бірнеше білім алушы, бір білім алушыда бірнеше құжат)
CREATE TABLE document_students (
    document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    student_id   INTEGER NOT NULL REFERENCES students(id)  ON DELETE CASCADE,
    note         TEXT,                            -- ескерту
    PRIMARY KEY (document_id, student_id)
);

-- 6. Қосымшаның пайдаланушылары (жүйеге кіру үшін)
CREATE TABLE users (
    id             INTEGER PRIMARY KEY,
    username       TEXT    NOT NULL UNIQUE,
    password_hash  TEXT    NOT NULL,              -- құпиясөз ашық сақталмайды
    role           TEXT    NOT NULL CHECK (role IN ('admin', 'visitor')),
    full_name      TEXT
);

-- Іздеуді жылдамдататын индекстер
CREATE INDEX idx_documents_date   ON documents(doc_date);
CREATE INDEX idx_documents_status ON documents(status);

-- Көрініс: тіркеу журналы (үш кесте біріктірілген)
CREATE VIEW v_registry AS
SELECT d.id, d.reg_number, d.doc_date, t.code AS type_code, t.name AS doc_type,
       t.category, d.title, dep.short_name AS department, d.author,
       d.status, d.academic_year, d.pages
  FROM documents d
  JOIN document_types t ON t.id = d.type_id
  JOIN departments dep  ON dep.id = d.department_id;

-- Триггер: бекітілген немесе мұрағаттағы құжатты жоюға тыйым салады
CREATE TRIGGER trg_protect_approved
BEFORE DELETE ON documents
WHEN OLD.status IN ('бекітілді', 'мұрағатта')
BEGIN
    SELECT RAISE(ABORT, 'Бекітілген немесе мұрағаттағы құжатты жоюға болмайды');
END;
