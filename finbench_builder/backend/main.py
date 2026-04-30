from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import database as db
from scraper import fetch_all_feeds, fetch_article_content, chunk_text
from prices import fetch_price_movement

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

db.init_db()

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


# ── Articles ──────────────────────────────────────────────────────────────────

@app.route("/api/articles", methods=["GET"])
def list_articles():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    article_type = request.args.get("type")
    entity_type = request.args.get("entity_type")

    articles, total = db.get_articles(page, per_page, article_type, entity_type)
    return jsonify({
        "articles": articles,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    })


@app.route("/api/articles/<int:article_id>", methods=["GET"])
def get_article(article_id):
    article = db.get_article(article_id)
    if not article:
        return jsonify({"error": "Not found"}), 404
    chunks = db.get_chunks(article_id)
    article["chunks"] = chunks
    return jsonify(article)


@app.route("/api/articles", methods=["POST"])
def add_article():
    data = request.json
    article_id = db.insert_article(
        title=data["title"],
        content=data["content"],
        source=data.get("source", "manual"),
        url=data.get("url", f"manual-{data['title'][:30]}"),
        published_at=data.get("published_at", ""),
        article_type=data.get("article_type", "news"),
        entity=data.get("entity", ""),
        entity_type=data.get("entity_type", "equity"),
    )
    if article_id:
        # Auto-chunk
        chunks = chunk_text(data["content"])
        db.save_chunks(article_id, chunks)
    return jsonify({"id": article_id, "status": "ok"})


@app.route("/api/articles/<int:article_id>/chunk", methods=["POST"])
def rechunk_article(article_id):
    article = db.get_article(article_id)
    if not article:
        return jsonify({"error": "Not found"}), 404
    target = int(request.json.get("target_tokens", 75))
    chunks = chunk_text(article["content"], target_tokens=target)
    db.save_chunks(article_id, chunks)
    return jsonify({"chunks": chunks, "count": len(chunks)})


@app.route("/api/articles/<int:article_id>/fetch-content", methods=["POST"])
def fetch_content(article_id):
    article = db.get_article(article_id)
    if not article:
        return jsonify({"error": "Not found"}), 404
    content = fetch_article_content(article["url"])
    if content:
        conn = db.get_db()
        conn.execute("UPDATE articles SET content = ? WHERE id = ?", (content, article_id))
        conn.commit()
        conn.close()
        chunks = chunk_text(content)
        db.save_chunks(article_id, chunks)
        return jsonify({"content_length": len(content), "chunks": len(chunks)})
    return jsonify({"error": "Could not fetch content"}), 400


# ── Chunks & Annotation ───────────────────────────────────────────────────────

@app.route("/api/chunks/<int:chunk_id>/label", methods=["POST"])
def label_chunk(chunk_id):
    label = request.json.get("label")
    if label is None or label == "":
        conn = db.get_db()
        conn.execute("UPDATE chunks SET label = NULL, annotated_at = NULL WHERE id = ?", (chunk_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "cleared": True})
    if label not in ("positive", "negative", "neutral"):
        return jsonify({"error": "Invalid label"}), 400
    db.update_chunk_label(chunk_id, label)
    return jsonify({"status": "ok"})


@app.route("/api/chunks/next-unlabeled", methods=["GET"])
def next_unlabeled():
    """Return the next chunk needing annotation."""
    article_type = request.args.get("type")
    entity_type = request.args.get("entity_type")
    exclude = request.args.get("exclude", "")
    exclude_ids = [int(x) for x in exclude.split(",") if x.strip().isdigit()]
    conn = db.get_db()
    conditions = ["ch.label IS NULL"]
    params = []
    if article_type:
        conditions.append("a.article_type = ?")
        params.append(article_type)
    if entity_type:
        conditions.append("a.entity_type = ?")
        params.append(entity_type)
    if exclude_ids:
        placeholders = ",".join("?" * len(exclude_ids))
        conditions.append(f"ch.id NOT IN ({placeholders})")
        params.extend(exclude_ids)
    where = "WHERE " + " AND ".join(conditions)
    conn.row_factory = db.sqlite3.Row
    row = conn.execute(f"""
        SELECT ch.*, a.id as article_id, a.title, a.source, a.url,
               a.article_type, a.entity, a.entity_type, a.published_at
        FROM chunks ch
        JOIN articles a ON ch.article_id = a.id
        {where}
        ORDER BY ch.id
        LIMIT 1
    """, params).fetchone()
    if not row:
        conn.close()
        return jsonify({"done": True})
    out = dict(row)
    qrows = conn.execute(
        "SELECT * FROM questions WHERE chunk_id = ? ORDER BY id",
        (out["id"],)
    ).fetchall()
    out["questions"] = [dict(q) for q in qrows]
    conn.close()
    return jsonify(out)


# ── Scraping ──────────────────────────────────────────────────────────────────

@app.route("/api/scrape", methods=["POST"])
def scrape():
    """Fetch articles from all RSS feeds and store them."""
    articles = fetch_all_feeds()
    added = 0
    for a in articles:
        aid = db.insert_article(
            title=a["title"],
            content=a["content"],
            source=a["source"],
            url=a["url"],
            published_at=a["published_at"],
            article_type=a["article_type"],
            entity=a["entity"],
            entity_type=a["entity_type"],
        )
        if aid:
            if a["content"]:
                chunks = chunk_text(a["content"])
                if chunks:
                    db.save_chunks(aid, chunks)
            added += 1
    return jsonify({"fetched": len(articles), "new": added})


# ── Price ─────────────────────────────────────────────────────────────────────

@app.route("/api/articles/<int:article_id>/price", methods=["GET"])
def get_price(article_id):
    """Return cached or freshly-fetched price movement around the article's publish date."""
    article = db.get_article(article_id)
    if not article:
        return jsonify({"error": "Article not found"}), 404

    force = request.args.get("refresh") == "1"

    # Cached?
    if not force and article.get("price_data"):
        try:
            return jsonify({"cached": True, "price": json.loads(article["price_data"])})
        except Exception:
            pass

    ticker = (article.get("entity") or "").strip()
    if not ticker:
        return jsonify({"price": None, "reason": "no_ticker"})

    price = fetch_price_movement(ticker, article.get("published_at", ""))
    if price:
        db.set_article_price_data(article_id, json.dumps(price))
    return jsonify({"price": price, "cached": False})


@app.route("/api/articles/<int:article_id>/entity", methods=["POST"])
def set_entity(article_id):
    """Allow user to set or correct the ticker on an article."""
    entity = (request.json.get("entity") or "").strip()
    conn = db.get_db()
    conn.execute("UPDATE articles SET entity = ?, price_data = NULL WHERE id = ?",
                 (entity, article_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "entity": entity})


# ── Questions ─────────────────────────────────────────────────────────────────

@app.route("/api/chunks/<int:chunk_id>/questions", methods=["GET"])
def list_questions(chunk_id):
    return jsonify(db.get_questions_for_chunk(chunk_id))


@app.route("/api/chunks/<int:chunk_id>/questions", methods=["POST"])
def create_question(chunk_id):
    data = request.json or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    qid = db.add_question(
        chunk_id=chunk_id,
        question=question,
        answer=data.get("answer"),
        notes=data.get("notes"),
    )
    return jsonify({"id": qid, "status": "ok"})


@app.route("/api/questions/<int:question_id>", methods=["PATCH"])
def patch_question(question_id):
    data = request.json or {}
    db.update_question(
        question_id,
        question=data.get("question"),
        answer=data.get("answer"),
        notes=data.get("notes"),
    )
    return jsonify({"status": "ok"})


@app.route("/api/questions/<int:question_id>", methods=["DELETE"])
def remove_question(question_id):
    db.delete_question(question_id)
    return jsonify({"status": "ok"})


# ── Export ────────────────────────────────────────────────────────────────────

@app.route("/api/export", methods=["GET"])
def export_data():
    labeled_only = request.args.get("labeled_only", "true").lower() == "true"
    fmt = request.args.get("format", "json")
    mode = request.args.get("mode", "questions")  # "questions" | "chunks"

    if mode == "questions":
        rows = db.get_questions_export(answered_only=labeled_only)
        filename = "benchmark_questions"
    else:
        rows = db.get_export_data(labeled_only)
        filename = "benchmark_chunks"

    if fmt == "jsonl":
        lines = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
        from flask import Response
        return Response(lines, mimetype="application/x-ndjson",
                        headers={"Content-Disposition": f"attachment;filename={filename}.jsonl"})
    return jsonify(rows)


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
def stats():
    return jsonify(db.get_stats())


if __name__ == "__main__":
    print("Starting Financial Benchmark server on http://localhost:5000")
    app.run(debug=True, port=5000)
