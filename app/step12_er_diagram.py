"""
12-қадам. Деректер базасының диаграммасын құру.

Кестелердің өрістері мен байланыстары базаның жүйелік каталогынан
(PRAGMA table_info, PRAGMA foreign_key_list) оқылады да, matplotlib
кітапханасы арқылы er_diagram.png суретіне салынады.
Қосымша кітапхана қажет: pip install matplotlib
"""
import logging
import sqlite3

from database import BASE_DIR, DB_PATH

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
except ImportError:
    raise SystemExit("matplotlib орнатылмаған: pip install matplotlib")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)   # қаріп ескертулерін жасыру

print("=" * 64)
print("12-ҚАДАМ. ДЕРЕКТЕР БАЗАСЫНЫҢ ДИАГРАММАСЫН ҚҰРУ")
print("=" * 64)

# 1. Метадеректерді оқу
conn = sqlite3.connect(DB_PATH)
tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
columns, links = {}, []
for t in tables:
    fk_cols = {}
    for fk in conn.execute(f"PRAGMA foreign_key_list({t})"):
        fk_cols[fk[3]] = fk[2]
        links.append((t, fk[3], fk[2], fk[4]))          # (кесте, өріс, сілтеме кестесі, сілтеме өрісі)
    columns[t] = [(name, ctype, pk > 0, name in fk_cols)
                  for _, name, ctype, _, _, pk in conn.execute(f"PRAGMA table_info({t})")]
conn.close()
print(f"Оқылды: {len(tables)} кесте, {len(links)} сыртқы кілт.")
for t, col, ref, ref_col in links:
    print(f"  {t}.{col} → {ref}.{ref_col}")

# 2. Кестелердің орналасуы: (баған, жоғарғы шеті)
LABELS = {"departments": "Бөлімшелер", "document_types": "Құжат түрлері",
          "documents": "Құжаттар", "document_students": "Құжат – білім алушы",
          "students": "Білім алушылар", "users": "Пайдаланушылар"}
PLACE = {"document_types": (0, 0.15), "departments": (0, 1.90), "documents": (1, 0.15),
         "document_students": (2, 0.15), "students": (3, 0.15), "users": (2, 1.40)}
COL_X = [0.15, 2.40, 4.65, 6.90]
BOX_W, HEAD_H, ROW_H = 1.75, 0.36, 0.17
COLOR = {"documents": "#9C2F2F", "users": "#5F6B7A"}
FONT = ["Arial", "Liberation Sans", "DejaVu Sans"]
MONO = ["Consolas", "DejaVu Sans Mono"]

boxes = {}
for t, (col, top) in PLACE.items():
    boxes[t] = (COL_X[col], top, BOX_W, HEAD_H + ROW_H * len(columns[t]) + 0.06)
fig_w = COL_X[-1] + BOX_W + 0.15
fig_h = max(y + h for x, y, w, h in boxes.values()) + 0.30
fig = plt.figure(figsize=(fig_w, fig_h), dpi=300)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, fig_w)
ax.set_ylim(fig_h, 0)
ax.axis("off")


def row_y(table, column):
    """Кестедегі өріс жолының ортасының y координаты."""
    x, y, w, h = boxes[table]
    names = [c[0] for c in columns[table]]
    return y + HEAD_H + ROW_H * (names.index(column) + 0.5) + 0.03


# 3. Кестелерді салу
for t, (x, y, w, h) in boxes.items():
    color = COLOR.get(t, "#1F3A5F")
    ax.add_patch(Rectangle((x, y), w, h, facecolor="white", edgecolor=color, lw=1.2, zorder=3))
    ax.add_patch(Rectangle((x, y), w, HEAD_H, facecolor=color, edgecolor=color, lw=1.2, zorder=3))
    ax.text(x + 0.08, y + 0.13, LABELS[t], color="white", fontsize=7.4, weight="bold",
            family=FONT, va="center", zorder=4)
    ax.text(x + 0.08, y + 0.27, t, color="#E8EEF5", fontsize=6.0, family=MONO, va="center", zorder=4)
    for name, ctype, pk, fk in columns[t]:
        cy = row_y(t, name)
        if pk:
            ax.text(x + 0.08, cy, "PK", fontsize=5.4, weight="bold", family=FONT, va="center",
                    color="#9C2F2F", zorder=4)
        if fk:
            ax.text(x + (0.24 if pk else 0.08), cy, "FK", fontsize=5.4, weight="bold", family=FONT,
                    va="center", color="#2E6F6F", zorder=4)
        ax.text(x + 0.44, cy, name, fontsize=6.2, family=MONO, va="center", zorder=4,
                weight="bold" if pk else "normal")
        ax.text(x + w - 0.08, cy, ctype.lower(), fontsize=5.4, family=MONO, va="center",
                ha="right", color="#6b7280", zorder=4)

# 4. Байланыстар: көп жақтан (FK) бір жаққа (PK) тік және көлденең сызықтар
LANES = {("documents", "type_id"): 2.05, ("documents", "department_id"): 2.20,
         ("document_students", "document_id"): 4.40, ("document_students", "student_id"): 6.70}
for t, col, ref, ref_col in links:
    x1, y1 = boxes[t][0], row_y(t, col)                 # FK өрісі (сол жақ шеті)
    x2, y2 = boxes[ref][0] + BOX_W, row_y(ref, ref_col)   # PK өрісі (оң жақ шеті)
    if boxes[ref][0] > boxes[t][0]:                     # сілтеме кестесі оң жақта тұрса
        x1, x2 = boxes[t][0] + BOX_W, boxes[ref][0]
    lane = LANES[(t, col)]
    ax.plot([x1, lane, lane, x2], [y1, y1, y2, y2], color="#4A5563", lw=1.0, zorder=2)
    ax.text(x1 + (0.05 if x1 < lane else -0.05), y1 - 0.06, "∞", fontsize=7,
            ha="left" if x1 < lane else "right", color="#4A5563", zorder=4)
    ax.text(x2 + (-0.05 if x2 > lane else 0.05), y2 - 0.06, "1", fontsize=6.5,
            ha="right" if x2 > lane else "left", color="#4A5563", zorder=4)

ax.text(COL_X[0], fig_h - 0.10, "PK – бастапқы кілт,  FK – сыртқы кілт,  1 — ∞ – «бірге-көп» байланыс",
        fontsize=6.2, family=FONT, color="#374151", va="center")
out = BASE_DIR / "er_diagram.png"
fig.savefig(out, dpi=300, facecolor="white")
plt.close(fig)
print(f"\nДиаграмма сақталды: {out.name}")
print("12-қадам аяқталды.")
