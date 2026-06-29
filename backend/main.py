"""回复军师 ReplyCoach — FastAPI 入口。

启动（在 reply-coach 目录下）：
    uvicorn backend.main:app --reload --port 8000
或：
    python3 -m backend.main
"""

import json
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import db, engine, personas

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="回复军师 ReplyCoach")
db.init()


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_B64_CHARS = 7_000_000


class GenerateRequest(BaseModel):
    scenario: str
    my_persona: str = ""
    their_persona: str = ""
    my_sliders: Dict[str, int] = {}
    their_sliders: Dict[str, int] = {}
    received: str = ""
    chat_history: str = ""
    relation_stage: str = ""
    relation_text: str = ""
    my_detail: str = ""
    their_detail: str = ""
    my_gender: str = ""
    their_gender: str = ""
    intent: str = ""
    image_data: str = ""
    image_media_type: str = ""


class ArchiveRequest(BaseModel):
    name: str = ""
    scenario: str
    my_persona: str = ""
    their_persona: str = ""
    my_sliders: Dict[str, int] = {}
    their_sliders: Dict[str, int] = {}
    my_detail: str = ""
    their_detail: str = ""
    relation_stage: str = ""
    relation_text: str = ""
    chat_history: str = ""
    my_gender: str = ""
    their_gender: str = ""


class SummaryRequest(BaseModel):
    scenario: str
    my_persona: str = ""
    their_persona: str = ""
    my_sliders: Dict[str, int] = {}
    their_sliders: Dict[str, int] = {}
    chat_history: str
    relation_stage: str = ""
    relation_text: str = ""
    my_detail: str = ""
    their_detail: str = ""
    my_gender: str = ""
    their_gender: str = ""


class ConsultRequest(BaseModel):
    scenario: str
    my_persona: str = ""
    their_persona: str = ""
    my_sliders: Dict[str, int] = {}
    their_sliders: Dict[str, int] = {}
    chat_history: str = ""
    question: str
    relation_stage: str = ""
    relation_text: str = ""
    my_detail: str = ""
    their_detail: str = ""
    my_gender: str = ""
    their_gender: str = ""


class CritiqueRequest(BaseModel):
    scenario: str
    my_persona: str = ""
    their_persona: str = ""
    my_sliders: Dict[str, int] = {}
    their_sliders: Dict[str, int] = {}
    chat_history: str = ""
    draft: str
    relation_stage: str = ""
    relation_text: str = ""
    my_detail: str = ""
    their_detail: str = ""
    my_gender: str = ""
    their_gender: str = ""


class ProfileRequest(BaseModel):
    side: str  # "me" | "their"
    scenario: str = ""
    tags: str = ""
    gender: str = ""
    free_text: str = ""
    chat_history: str = ""


class ArchiveUpdateRequest(BaseModel):
    name: Optional[str] = None
    scenario: Optional[str] = None
    my_persona: Optional[str] = None
    their_persona: Optional[str] = None
    my_detail: Optional[str] = None
    their_detail: Optional[str] = None
    relation_stage: Optional[str] = None
    relation_text: Optional[str] = None
    chat_history: Optional[str] = None
    my_gender: Optional[str] = None
    their_gender: Optional[str] = None
    hidden: Optional[int] = None
    my_sliders: Optional[Dict[str, int]] = None
    their_sliders: Optional[Dict[str, int]] = None


def _profiles(scenario, my_sliders, their_sliders):
    """把两边的滑轨值翻成画像描述字符串，喂给引擎。"""
    return (personas.describe_sliders(scenario, my_sliders or {}),
            personas.describe_sliders(scenario, their_sliders or {}))


def _with_relation(chat_history: str, relation_text: str) -> str:
    """把关系近况自由文本注入到聊天上下文顶部，供模型理解背景。"""
    rt = (relation_text or "").strip()
    if not rt:
        return chat_history
    return f"【关系近况】{rt}\n———\n{chat_history}" if chat_history else f"【关系近况】{rt}"


@app.get("/api/meta")
def meta():
    return {
        "scenarios": personas.SCENARIOS,
        "relation_stages": personas.RELATION_STAGES,
        "genders": personas.GENDERS,
        "tones": personas.TONES,
        "engine": engine.engine_mode(),
    }


@app.post("/api/generate")
def generate(req: GenerateRequest):
    scenario = personas.by_id(personas.SCENARIOS, req.scenario)
    if not scenario:
        raise HTTPException(400, "无效的场景 id")
    my_profile, their_profile = _profiles(scenario, req.my_sliders, req.their_sliders)

    received = req.received.strip()
    chat_history = _with_relation(req.chat_history.strip(), req.relation_text)

    image = None
    if req.image_data:
        if req.image_media_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(400, "不支持的图片格式（支持 jpeg/png/webp/gif）")
        if len(req.image_data) > MAX_IMAGE_B64_CHARS:
            raise HTTPException(400, "图片太大，请控制在 5MB 以内")
        image = {"data": req.image_data, "media_type": req.image_media_type}

    if not chat_history and not received and not image:
        raise HTTPException(400, "请提供聊天记录或对方消息，或上传截图")
    if not chat_history and not received and image and not engine.llm_available():
        raise HTTPException(400, "离线引擎无法识别图片内容：请粘贴文字消息，或设置 ANTHROPIC_API_KEY 启用截图识别")

    result, used_engine = engine.generate(
        scenario, my_profile, their_profile, received, req.intent, image=image,
        chat_history=chat_history,
        relation_stage=req.relation_stage,
        my_detail=req.my_detail,
        their_detail=req.their_detail,
        my_gender=req.my_gender,
        their_gender=req.their_gender,
    )
    result["engine"] = used_engine

    # 数据库记录：用 received 或 chat_history 最后一行
    if received:
        received_for_db = received
    elif chat_history:
        last_lines = [l.strip() for l in chat_history.splitlines() if l.strip()]
        received_for_db = last_lines[-1][:200] if last_lines else ""
    else:
        received_for_db = result.get("extracted_received") or "[图片消息]"

    history_id = db.add(
        req.scenario, req.my_persona, req.their_persona,
        received_for_db, req.intent.strip(), result, has_image=bool(image),
    )
    return {"id": history_id, **result}


@app.post("/api/summary")
def summary(req: SummaryRequest):
    scenario = personas.by_id(personas.SCENARIOS, req.scenario)
    if not scenario:
        raise HTTPException(400, "无效的场景 id")
    my_profile, their_profile = _profiles(scenario, req.my_sliders, req.their_sliders)

    chat_history = req.chat_history.strip()
    if not chat_history:
        raise HTTPException(400, "关系分析需要聊天记录，请粘贴完整对话内容")
    chat_history = _with_relation(chat_history, req.relation_text)

    result, used_engine = engine.generate_summary(
        scenario, my_profile, their_profile, chat_history,
        relation_stage=req.relation_stage,
        my_detail=req.my_detail,
        their_detail=req.their_detail,
        my_gender=req.my_gender,
        their_gender=req.their_gender,
    )
    return {"engine": used_engine, **result}


@app.post("/api/consult")
def consult(req: ConsultRequest):
    scenario = personas.by_id(personas.SCENARIOS, req.scenario)
    if not scenario:
        raise HTTPException(400, "无效的场景 id")
    my_profile, their_profile = _profiles(scenario, req.my_sliders, req.their_sliders)
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "请告诉军师你想问什么")

    result, used_engine = engine.generate_consult(
        scenario, my_profile, their_profile, _with_relation(req.chat_history.strip(), req.relation_text), question,
        relation_stage=req.relation_stage,
        my_detail=req.my_detail, their_detail=req.their_detail,
        my_gender=req.my_gender, their_gender=req.their_gender,
    )
    return {"engine": used_engine, "question": question, **result}


@app.post("/api/critique")
def critique(req: CritiqueRequest):
    scenario = personas.by_id(personas.SCENARIOS, req.scenario)
    if not scenario:
        raise HTTPException(400, "无效的场景 id")
    my_profile, their_profile = _profiles(scenario, req.my_sliders, req.their_sliders)
    draft = req.draft.strip()
    if not draft:
        raise HTTPException(400, "把你想发的那句话填进来，军师才能评")

    result, used_engine = engine.generate_critique(
        scenario, my_profile, their_profile, _with_relation(req.chat_history.strip(), req.relation_text), draft,
        relation_stage=req.relation_stage,
        my_detail=req.my_detail, their_detail=req.their_detail,
        my_gender=req.my_gender, their_gender=req.their_gender,
    )
    return {"engine": used_engine, "draft": draft, **result}


@app.post("/api/profile")
def profile(req: ProfileRequest):
    scenario = personas.by_id(personas.SCENARIOS, req.scenario) if req.scenario else None
    text, used_engine = engine.generate_profile(
        req.side, scenario, tags=req.tags, gender=req.gender,
        free_text=req.free_text.strip(), chat_history=req.chat_history.strip(),
    )
    return {"engine": used_engine, "profile": text}


# ---- 历史记录 ----

@app.get("/api/history")
def history(limit: int = 30):
    return db.list_all(limit=min(limit, 100))


@app.delete("/api/history/{history_id}")
def delete_history(history_id: int):
    if not db.delete(history_id):
        raise HTTPException(404, "记录不存在")
    return {"ok": True}


@app.delete("/api/history")
def clear_history():
    db.clear()
    return {"ok": True}


# ---- 聊天归档 ----

def _parse_sliders(raw):
    if not raw:
        return {}
    try:
        val = json.loads(raw)
        return val if isinstance(val, dict) else {}
    except (ValueError, TypeError):
        return {}


@app.get("/api/archives")
def list_archives(hidden: int = 0, page: int = 1, page_size: int = 8):
    """分页返回档案列表。page 从 1 起；返回总数与总页数，供前端渲染分页控件。"""
    page = max(1, page)
    page_size = max(1, min(page_size, 50))
    total = db.count_archives(hidden=bool(hidden))
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, pages)
    offset = (page - 1) * page_size
    items = db.list_archives(hidden=bool(hidden), limit=page_size, offset=offset)
    for it in items:  # 滑轨 JSON 文本 → dict，方便前端直接用
        it["my_sliders"] = _parse_sliders(it.get("my_sliders"))
        it["their_sliders"] = _parse_sliders(it.get("their_sliders"))
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}


@app.post("/api/archives")
def save_archive(req: ArchiveRequest):
    name = req.name.strip()
    if not name:
        sc = personas.by_id(personas.SCENARIOS, req.scenario)
        name = f"{sc['name'] if sc else req.scenario} · 未命名"
    archive_id = db.add_archive(
        name, req.scenario, req.my_persona, req.their_persona,
        req.my_detail, req.their_detail, req.relation_stage, req.chat_history,
        my_gender=req.my_gender, their_gender=req.their_gender,
        relation_text=req.relation_text,
        my_sliders=json.dumps(req.my_sliders, ensure_ascii=False),
        their_sliders=json.dumps(req.their_sliders, ensure_ascii=False),
    )
    return {"id": archive_id, "name": name}


@app.put("/api/archives/{archive_id}")
def update_archive(archive_id: int, req: ArchiveUpdateRequest):
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    for key in ("my_sliders", "their_sliders"):  # 滑轨 dict → JSON 文本入库
        if key in fields:
            fields[key] = json.dumps(fields[key], ensure_ascii=False)
    if not db.update_archive(archive_id, **fields):
        raise HTTPException(404, "归档不存在或无可更新字段")
    return {"ok": True}


@app.delete("/api/archives/{archive_id}")
def delete_archive(archive_id: int):
    if not db.delete_archive(archive_id):
        raise HTTPException(404, "归档不存在")
    return {"ok": True}


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
