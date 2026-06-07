"""
RAG (Retrieval-Augmented Generation) service.

Embedding: SiliconFlow BAAI/bge-m3 (1024-dim, OpenAI-compatible)
Vector store: sqlite-vec (SQLite extension)
Generation: DeepSeek Chat API (OpenAI-compatible)

Configuration — set these environment variables or fill in directly:
  SILICONFLOW_API_KEY: SiliconFlow API key for embeddings
  DEEPSEEK_API_KEY   : DeepSeek API key for chat generation
  DEEPSEEK_BASE_URL  : defaults to https://api.deepseek.com/v1
"""

from __future__ import annotations

import os
import sqlite3
import struct

import sqlite_vec
from openai import OpenAI

from app.database import DB_PATH, get_connection

# ── Configuration ────────────────────────────────────────────────────────────

# Defaults from environment variables; overridden at runtime by DB values via get_config()
SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
EMBEDDING_MODEL = "BAAI/bge-m3"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

EMBEDDING_DIM = 1024  # BAAI/bge-m3 output dimension
TOP_K = 5             # number of chunks to retrieve


def get_config() -> dict:
    """Read RAG config from DB, fall back to env vars."""
    defaults = {
        "rag_siliconflow_api_key": os.environ.get("SILICONFLOW_API_KEY", ""),
        "rag_siliconflow_base_url": SILICONFLOW_BASE_URL,
        "rag_embedding_model": EMBEDDING_MODEL,
        "rag_deepseek_api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "rag_deepseek_base_url": DEEPSEEK_BASE_URL,
        "rag_deepseek_model": DEEPSEEK_MODEL,
    }
    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT key, value FROM app_config WHERE key LIKE 'rag_%'"
            ).fetchall()
        for row in rows:
            if row["value"]:
                defaults[row["key"]] = row["value"]
    except Exception:
        pass
    return defaults


# ── Helpers ───────────────────────────────────────────────────────────────────

def _vec_conn() -> sqlite3.Connection:
    """Return a connection with sqlite-vec loaded."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def _serialize(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _embed(text: str) -> list[float]:
    cfg = get_config()
    client = OpenAI(api_key=cfg["rag_siliconflow_api_key"], base_url=cfg["rag_siliconflow_base_url"])
    resp = client.embeddings.create(model=cfg["rag_embedding_model"], input=text)
    return resp.data[0].embedding


# ── Vector table init ─────────────────────────────────────────────────────────

def initialize_vec_table() -> None:
    """Create the vec0 virtual table if it doesn't exist."""
    with _vec_conn() as conn:
        conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS entries_vec "
            f"USING vec0(entry_id INTEGER PRIMARY KEY, embedding FLOAT[{EMBEDDING_DIM}])"
        )


# ── Indexing ──────────────────────────────────────────────────────────────────

def _text_for_entry(entry_id: int) -> str:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT title, summary, cleaned_markdown FROM entries WHERE id = ?",
            (entry_id,),
        ).fetchone()
    if row is None:
        return ""
    parts = [row["title"] or "", row["summary"] or "", (row["cleaned_markdown"] or "")[:2000]]
    return "\n".join(p for p in parts if p)


def index_entry(entry_id: int) -> None:
    """Embed a single entry and upsert into the vector table."""
    text = _text_for_entry(entry_id)
    if not text.strip():
        return
    vec = _embed(text)
    with _vec_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO entries_vec(entry_id, embedding) VALUES (?, ?)",
            (entry_id, _serialize(vec)),
        )


def index_all_entries() -> int:
    """Embed all entries that are not yet in the vector table. Returns count indexed."""
    with get_connection() as conn:
        rows = conn.execute("SELECT id FROM entries").fetchall()
    with _vec_conn() as conn:
        already = {r[0] for r in conn.execute("SELECT entry_id FROM entries_vec").fetchall()}
    pending = [r["id"] for r in rows if r["id"] not in already]
    for entry_id in pending:
        try:
            index_entry(entry_id)
        except Exception:
            pass
    return len(pending)


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(query: str, top_k: int = TOP_K) -> list[dict]:
    """Return top-k articles most similar to the query."""
    q_vec = _embed(query)
    with _vec_conn() as conn:
        rows = conn.execute(
            """
            SELECT entry_id, distance
            FROM entries_vec
            WHERE embedding MATCH ?
              AND k = ?
            ORDER BY distance
            """,
            (_serialize(q_vec), top_k),
        ).fetchall()
    if not rows:
        return []
    entry_ids = [r["entry_id"] for r in rows]
    distance_map = {r["entry_id"]: r["distance"] for r in rows}
    placeholders = ",".join("?" * len(entry_ids))
    with get_connection() as conn:
        entries = conn.execute(
            f"""
            SELECT entries.id, entries.title, entries.link, entries.summary,
                   entries.cleaned_markdown, entries.published_at,
                   feeds.title AS feed_title
            FROM entries
            JOIN feeds ON feeds.id = entries.feed_id
            WHERE entries.id IN ({placeholders})
            """,
            entry_ids,
        ).fetchall()
    result = []
    for e in entries:
        result.append({
            "id": e["id"],
            "title": e["title"],
            "url": e["link"] or "",
            "feed_title": e["feed_title"],
            "published_at": e["published_at"],
            "summary": e["summary"],
            "snippet": (e["cleaned_markdown"] or e["summary"] or "")[:500],
            "distance": distance_map.get(e["id"], 9999),
        })
    result.sort(key=lambda x: x["distance"])
    return result


# ── Generation ────────────────────────────────────────────────────────────────

def ask(question: str) -> dict:
    """Full RAG pipeline: retrieve relevant articles then generate an answer."""
    sources = retrieve(question)
    if not sources:
        return {
            "answer": "暂时没有找到相关文章，请先同步订阅源或等待向量索引完成。",
            "sources": [],
        }

    context_parts = []
    for i, s in enumerate(sources, 1):
        context_parts.append(
            f"[{i}] 标题：{s['title']}\n来源：{s['feed_title']}\n内容片段：{s['snippet']}"
        )
    context = "\n\n".join(context_parts)

    system_prompt = (
        "你是一个 RSS 阅读助手。根据下面提供的文章片段回答用户问题。"
        "回答要简洁、准确，并在末尾用 [1][2] 等编号标注引用来源。"
        "如果文章片段中没有足够信息，请如实说明。"
    )
    user_prompt = f"以下是检索到的相关文章：\n\n{context}\n\n用户问题：{question}"

    from openai import OpenAI
    cfg = get_config()
    client = OpenAI(api_key=cfg["rag_deepseek_api_key"], base_url=cfg["rag_deepseek_base_url"])
    resp = client.chat.completions.create(
        model=cfg["rag_deepseek_model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=1024,
    )
    answer = resp.choices[0].message.content or ""

    return {"answer": answer, "sources": sources}
