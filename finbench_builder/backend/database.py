import sqlite3
import json
from datetime import datetime

DB_PATH = "benchmark.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT,
            url TEXT UNIQUE,
            published_at TEXT,
            article_type TEXT DEFAULT 'news',
            entity TEXT,
            entity_type TEXT DEFAULT 'equity',
            fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER,
            chunk_index INTEGER,
            text TEXT NOT NULL,
            token_count INTEGER,
            label TEXT,
            annotated_at TEXT,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
        )
    """)

    # Migration: add price_data column to articles if it doesn't exist
    try:
        c.execute("ALTER TABLE articles ADD COLUMN price_data TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


# ── Price cache ────────────────────────────────────────────────────────────
def set_article_price_data(article_id, price_json):
    conn = get_db()
    conn.execute("UPDATE articles SET price_data = ? WHERE id = ?", (price_json, article_id))
    conn.commit()
    conn.close()


def get_article_price_data(article_id):
    conn = get_db()
    row = conn.execute("SELECT price_data FROM articles WHERE id = ?", (article_id,)).fetchone()
    conn.close()
    return row["price_data"] if row else None


# ── Questions ──────────────────────────────────────────────────────────────
def add_question(chunk_id, question, answer=None, notes=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO questions (chunk_id, question, answer, notes)
        VALUES (?, ?, ?, ?)
    """, (chunk_id, question, answer, notes))
    conn.commit()
    qid = c.lastrowid
    conn.close()
    return qid


def get_questions_for_chunk(chunk_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM questions WHERE chunk_id = ? ORDER BY id",
        (chunk_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_question(question_id, question=None, answer=None, notes=None):
    conn = get_db()
    fields, params = [], []
    if question is not None:
        fields.append("question = ?"); params.append(question)
    if answer is not None:
        fields.append("answer = ?"); params.append(answer)
    if notes is not None:
        fields.append("notes = ?"); params.append(notes)
    if fields:
        params.append(question_id)
        conn.execute(f"UPDATE questions SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
    conn.close()


def delete_question(question_id):
    conn = get_db()
    conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()


def get_questions_export(answered_only=True):
    conn = get_db()
    cond = "WHERE q.answer IS NOT NULL AND q.answer != ''" if answered_only else ""
    rows = conn.execute(f"""
        SELECT q.id as question_id, q.question, q.answer, q.notes, q.created_at,
               ch.id as chunk_id, ch.text as context, ch.label as chunk_label,
               ch.token_count,
               a.title, a.source, a.url, a.published_at,
               a.article_type, a.entity, a.entity_type, a.price_data
        FROM questions q
        JOIN chunks ch ON q.chunk_id = ch.id
        JOIN articles a ON ch.article_id = a.id
        {cond}
        ORDER BY q.id
    """).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        # Inline parsed price summary so each record is self-contained
        if d.get("price_data"):
            try:
                pd = json.loads(d["price_data"])
                d["price_change_pct"] = pd.get("change_pct")
                d["price_before"] = pd.get("before_price")
                d["price_after"] = pd.get("after_price")
            except Exception:
                pass
        d.pop("price_data", None)
        out.append(d)
    return out


def insert_article(title, content, source, url, published_at, article_type="news", entity="", entity_type="equity"):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR IGNORE INTO articles (title, content, source, url, published_at, article_type, entity, entity_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, content, source, url, published_at, article_type, entity, entity_type))
        conn.commit()
        return c.lastrowid
    except Exception as e:
        print(f"Insert error: {e}")
        return None
    finally:
        conn.close()


def get_articles(page=1, per_page=20, article_type=None, entity_type=None, labeled=None):
    conn = get_db()
    c = conn.cursor()
    conditions = []
    params = []

    if article_type:
        conditions.append("article_type = ?")
        params.append(article_type)
    if entity_type:
        conditions.append("entity_type = ?")
        params.append(entity_type)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * per_page

    c.execute(f"""
        SELECT a.*,
               COUNT(ch.id) as chunk_count,
               SUM(CASE WHEN ch.label IS NOT NULL THEN 1 ELSE 0 END) as labeled_count
        FROM articles a
        LEFT JOIN chunks ch ON a.id = ch.article_id
        {where}
        GROUP BY a.id
        ORDER BY a.fetched_at DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])

    rows = [dict(r) for r in c.fetchall()]

    c.execute(f"SELECT COUNT(*) FROM articles a {where}", params)
    total = c.fetchone()[0]

    conn.close()
    return rows, total


def get_article(article_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def save_chunks(article_id, chunks):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM chunks WHERE article_id = ?", (article_id,))
    for i, chunk in enumerate(chunks):
        c.execute("""
            INSERT INTO chunks (article_id, chunk_index, text, token_count, label)
            VALUES (?, ?, ?, ?, ?)
        """, (article_id, i, chunk["text"], chunk["token_count"], chunk.get("label")))
    conn.commit()
    conn.close()


def get_chunks(article_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM chunks WHERE article_id = ? ORDER BY chunk_index", (article_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def update_chunk_label(chunk_id, label):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE chunks SET label = ?, annotated_at = ? WHERE id = ?",
              (label, datetime.now().isoformat(), chunk_id))
    conn.commit()
    conn.close()


def get_export_data(labeled_only=True):
    conn = get_db()
    c = conn.cursor()
    cond = "WHERE ch.label IS NOT NULL" if labeled_only else ""
    c.execute(f"""
        SELECT ch.id as chunk_id, ch.text, ch.label, ch.token_count,
               a.title, a.source, a.url, a.published_at,
               a.article_type, a.entity, a.entity_type
        FROM chunks ch
        JOIN articles a ON ch.article_id = a.id
        {cond}
        ORDER BY a.id, ch.chunk_index
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM articles")
    total_articles = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM chunks")
    total_chunks = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM chunks WHERE label IS NOT NULL")
    labeled_chunks = c.fetchone()[0]
    c.execute("SELECT label, COUNT(*) as cnt FROM chunks WHERE label IS NOT NULL GROUP BY label")
    label_dist = {row[0]: row[1] for row in c.fetchall()}
    c.execute("SELECT article_type, COUNT(*) as cnt FROM articles GROUP BY article_type")
    type_dist = {row[0]: row[1] for row in c.fetchall()}
    c.execute("SELECT entity_type, COUNT(*) as cnt FROM articles GROUP BY entity_type")
    entity_dist = {row[0]: row[1] for row in c.fetchall()}
    c.execute("SELECT COUNT(*) FROM questions")
    total_questions = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM questions WHERE answer IS NOT NULL AND answer != ''")
    answered_questions = c.fetchone()[0]
    conn.close()
    return {
        "total_articles": total_articles,
        "total_chunks": total_chunks,
        "labeled_chunks": labeled_chunks,
        "total_questions": total_questions,
        "answered_questions": answered_questions,
        "label_distribution": label_dist,
        "type_distribution": type_dist,
        "entity_distribution": entity_dist,
    }
