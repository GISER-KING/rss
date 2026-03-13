from fastapi import APIRouter, HTTPException
from fastapi import Body
from sse_starlette.sse import EventSourceResponse
from sqlmodel import select
from ..core.db import get_session
from ..db.models import User, Conversation, Message
from ..agents.river_agent import build_enhanced_agent, enhanced_stream_agent


router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/conversations")
def list_conversations(user_id: int):
    with get_session() as s:
        cs = s.exec(select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc())).all()
        return [{"id": c.id, "title": c.title, "mode": c.mode, "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat()} for c in cs]


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int):
    with get_session() as s:
        c = s.get(Conversation, conversation_id)
        if c:
            # Delete messages first
            messages = s.exec(select(Message).where(Message.conversation_id == conversation_id)).all()
            for m in messages:
                s.delete(m)
            # Delete conversation
            s.delete(c)
            s.commit()
        return {"ok": True}


@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: int):
    with get_session() as s:
        msgs = s.exec(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at)).all()
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "metadata": {"file_name": None} if not m.meta_info else {"file_name": m.meta_info}, # Simple adaptation
                "created_at": m.created_at.isoformat()
            }
            for m in msgs
        ]


@router.patch("/conversations/{conversation_id}")
def update_conversation(conversation_id: int, title: str = Body(..., embed=True)):
    with get_session() as s:
        c = s.get(Conversation, conversation_id)
        if not c:
             raise HTTPException(status_code=404, detail="conversation not found")
        c.title = title
        s.add(c)
        s.commit()
        return {"id": c.id, "title": c.title}


@router.post("/send")
def send_message(
    user_id: int = Body(...),
    conversation_id: int | None = Body(None),
    content: str = Body(...),
    mode: str = Body("chat"),
):
    with get_session() as s:
        u = s.get(User, user_id)
        if u is None:
            raise HTTPException(status_code=404, detail="user not found")
        if conversation_id is None:
            c = Conversation(user_id=user_id, title=content[:20] or "新对话", mode=mode)
            s.add(c)
            s.commit()
            s.refresh(c)
        else:
            c = s.get(Conversation, conversation_id)
            if c is None:
                raise HTTPException(status_code=404, detail="conversation not found")
        m = Message(conversation_id=c.id, role="user", content=content)
        s.add(m)
        s.commit()
        return {"conversation_id": c.id, "message_id": m.id}


@router.post("/stream")
async def stream_chat(
    user_id: int = Body(...),
    conversation_id: int = Body(...),
):
    with get_session() as s:
        u = s.get(User, user_id)
        if u is None:
            raise HTTPException(status_code=404, detail="user not found")
        c = s.get(Conversation, conversation_id)
        if c is None:
            raise HTTPException(status_code=404, detail="conversation not found")

        last = s.exec(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id.desc())
        ).first()
        if last is None:
            raise HTTPException(status_code=400, detail="no user message")

        # 使用增强型Agent（双流RAG + 任务感知 + 层次化提示）
        agent, dual_kb, solution_db = build_enhanced_agent(
            u.api_base_url, u.api_key, mode=c.mode
        )

    async def gen():
        try:
            generator = enhanced_stream_agent(
                agent, dual_kb, solution_db,
                last.content, str(conversation_id)
            )

            for chunk in generator:
                yield {"event": "message", "data": chunk}

            yield {"event": "end", "data": "[DONE]"}
        except Exception as e:
            print(f"Error during streaming: {e}")
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(gen())


@router.get("/knowledge/stats")
def knowledge_stats():
    """获取知识库统计信息"""
    from ..agents.river_agent import build_dual_stream_kb
    try:
        dual_kb = build_dual_stream_kb()
        return dual_kb.get_statistics()
    except Exception as e:
        return {
            "document_stream": {"count": 0},
            "data_stream": {"count": 0},
            "error": str(e)
        }
