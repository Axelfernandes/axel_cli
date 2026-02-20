from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import uuid
import json

from ..database import get_db
from ..models import User, Session
from ..services.ai import get_ai_client
from ..auth import get_current_user
from ..crypto import decrypt
from ..services.embeddings import get_embedding_service

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    provider: str
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    repo: Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    content: str
    session_id: str

def get_user_api_key(user: User, provider: str) -> Optional[str]:
    """Get and decrypt the user's API key for the given provider."""
    encrypted = None
    if provider == "openai":
        encrypted = user.openai_key
    elif provider == "anthropic":
        encrypted = user.anthropic_key
    elif provider == "gemini":
        encrypted = user.gemini_key
    elif provider == "cerebras":
        encrypted = user.cerebras_key
    
    return decrypt(encrypted) if encrypted else None

async def _get_user_from_header(authorization: Optional[str], db: AsyncSession) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    return await get_current_user(token=token, db=db)

@router.post("")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    user = await _get_user_from_header(authorization, db)
    
    api_key = get_user_api_key(user, request.provider)
    if not api_key and request.provider != "vertex_mistral":
        raise HTTPException(
            status_code=400,
            detail=f"No API key configured for {request.provider}. Please add your API key in settings."
        )
    
    ai_client = get_ai_client(request.provider, api_key or "")
    
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    try:
        result = await ai_client.chat(messages, model=request.model, temperature=request.temperature, max_tokens=request.max_tokens)
        content = result["content"]
        usage = result.get("usage")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")
    
    session_id = request.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        new_session = Session(
            id=session_id,
            user_id=user.id,
            repo_full_name=request.repo or "",
            messages=messages + [{"role": "assistant", "content": content}],
        )
        db.add(new_session)
    else:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if session:
            session.messages = session.messages + [{"role": "assistant", "content": content}]
            session.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"content": content, "session_id": session_id, "usage": usage}

@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    user = await _get_user_from_header(authorization, db)
    
    api_key = get_user_api_key(user, request.provider)
    if not api_key and request.provider != "vertex_mistral":
        raise HTTPException(
            status_code=400,
            detail=f"No API key configured for {request.provider}. Please add your API key in settings."
        )
    
    ai_client = get_ai_client(request.provider, api_key or "")
    
    # RAG: Retrieve context if repo is provided
    context = ""
    if request.repo:
        try:
            embedding_service = get_embedding_service(api_key=api_key)
            # Use the last message as the query
            query_text = request.messages[-1].content
            search_results = embedding_service.query(query_text)
            
            if search_results:
                context = "\n\nRelevant code snippets from the repository:\n"
                for res in search_results:
                    context += f"--- {res['metadata']['path']} ---\n{res['content']}\n"
        except Exception as e:
            # Non-blocking: log the error but proceed with chat
            print(f"RAG Error: {str(e)}")

    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    # Inject context into the first message or as a system message if supported
    if context:
        messages[0]["content"] = f"Context: {context}\n\nUser Question: {messages[0]['content']}"

    session_id = request.session_id or str(uuid.uuid4())
    full_content = []

    async def generate():
        try:
            async for chunk in ai_client.chat_stream(
                messages, model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            ):
                if "content" in chunk:
                    text = chunk["content"]
                    full_content.append(text)
                    yield f"data: {json.dumps({'content': text, 'session_id': session_id})}\n\n"
                if "usage" in chunk:
                    yield f"data: {json.dumps({'usage': chunk['usage'], 'session_id': session_id})}\n\n"
        except Exception as e:
            # Emit a proper error event so the frontend can display it
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
            return
        finally:
            # Save the full response to the session 
            if full_content:
                content = "".join(full_content)
                result = await db.execute(select(Session).where(Session.id == session_id))
                session = result.scalar_one_or_none()
                if session:
                    session.messages = session.messages + [{"role": "assistant", "content": content}]
                    session.updated_at = datetime.utcnow()
                else:
                    new_session = Session(
                        id=session_id,
                        user_id=user.id,
                        repo_full_name=request.repo or "",
                        messages=messages + [{"role": "assistant", "content": content}],
                    )
                    db.add(new_session)
                await db.commit()
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@router.get("/sessions")
async def list_sessions(
    repo: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    user = await _get_user_from_header(authorization, db)
    query = select(Session).where(Session.user_id == user.id)
    if repo:
        query = query.where(Session.repo_full_name == repo)
    query = query.order_by(Session.updated_at.desc()).limit(20)
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return {
        "sessions": [
            {
                "id": s.id,
                "repo_full_name": s.repo_full_name,
                "preview": s.messages[0]["content"][:80] if s.messages else "",
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sessions
        ]
    }

@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    user = await _get_user_from_header(authorization, db)
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "id": session.id,
        "repo_full_name": session.repo_full_name,
        "messages": session.messages,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }
