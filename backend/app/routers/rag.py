from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.database import get_connection

router = APIRouter()

_index_status = {"running": False, "last_added": 0, "last_removed": 0, "error": ""}


class AskRequest(BaseModel):
    question: str


class AskSource(BaseModel):
    id: int
    title: str
    url: str
    feed_title: str
    published_at: str | None = None
    snippet: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[AskSource]


class RagConfig(BaseModel):
    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"


@router.get("/config", response_model=RagConfig)
def get_rag_config():
    from app.services.rag_service import get_config
    cfg = get_config()
    return RagConfig(
        siliconflow_api_key=cfg["rag_siliconflow_api_key"],
        siliconflow_base_url=cfg["rag_siliconflow_base_url"],
        embedding_model=cfg["rag_embedding_model"],
        embedding_dim=int(cfg.get("rag_embedding_dim", 1024)),
        deepseek_api_key=cfg["rag_deepseek_api_key"],
        deepseek_base_url=cfg["rag_deepseek_base_url"],
        deepseek_model=cfg["rag_deepseek_model"],
    )


@router.put("/config", response_model=RagConfig)
def save_rag_config(body: RagConfig):
    mapping = {
        "rag_siliconflow_api_key": body.siliconflow_api_key,
        "rag_siliconflow_base_url": body.siliconflow_base_url,
        "rag_embedding_model": body.embedding_model,
        "rag_embedding_dim": str(body.embedding_dim),
        "rag_deepseek_api_key": body.deepseek_api_key,
        "rag_deepseek_base_url": body.deepseek_base_url,
        "rag_deepseek_model": body.deepseek_model,
    }
    with get_connection() as conn:
        for key, value in mapping.items():
            conn.execute(
                "INSERT INTO app_config(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
    # reinitialize vec table in case embedding_dim changed
    try:
        from app.services.rag_service import initialize_vec_table
        initialize_vec_table()
    except Exception:
        pass
    return body


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    if not body.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty")
    try:
        from app.services.rag_service import ask as rag_ask
        result = rag_ask(body.question)
        return result
    except Exception as exc:
        msg = str(exc)
        if "connection" in msg.lower() or "connect" in msg.lower():
            detail = "无法连接到 AI 服务，请检查 Base URL 是否正确"
        elif "401" in msg or "authentication" in msg.lower() or "api key" in msg.lower():
            detail = "API Key 无效或已过期，请在 AI 设置中重新配置"
        elif "model" in msg.lower() and "not found" in msg.lower():
            detail = "模型不存在，请检查 AI 设置中的模型名称"
        else:
            detail = f"AI 服务调用失败：{msg}"
        raise HTTPException(status_code=500, detail=detail) from exc


def _run_index():
    _index_status["running"] = True
    _index_status["error"] = ""
    try:
        from app.services.rag_service import index_all_entries
        result = index_all_entries()
        _index_status["last_added"] = result["added"]
        _index_status["last_removed"] = result["removed"]
    except Exception as exc:
        msg = str(exc)
        if "connection" in msg.lower() or "connect" in msg.lower():
            _index_status["error"] = "无法连接到 Embedding 服务，请检查 Base URL 是否正确"
        elif "401" in msg or "authentication" in msg.lower() or "api key" in msg.lower():
            _index_status["error"] = "Embedding API Key 无效，请在 AI 设置中重新配置"
        else:
            _index_status["error"] = f"索引失败：{msg}"
    finally:
        _index_status["running"] = False


@router.post("/index", response_model=dict)
def trigger_index(background_tasks: BackgroundTasks):
    if _index_status["running"]:
        return {"status": "already_running", "message": "索引正在进行中，请稍候"}
    background_tasks.add_task(_run_index)
    return {"status": "started", "message": "索引已在后台启动"}


@router.get("/index/status", response_model=dict)
def index_status():
    return {
        "running": _index_status["running"],
        "last_added": _index_status["last_added"],
        "last_removed": _index_status["last_removed"],
        "error": _index_status["error"],
    }
