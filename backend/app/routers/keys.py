from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models import User
from ..auth import get_current_user
from ..crypto import encrypt, decrypt

router = APIRouter(prefix="/keys", tags=["keys"])

class SetKeyRequest(BaseModel):
    provider: str
    api_key: str

@router.get("")
async def get_keys(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token=token, db=db)
    
    return {
        "openai": bool(user.openai_key),
        "anthropic": bool(user.anthropic_key),
        "gemini": bool(user.gemini_key),
        "cerebras": bool(user.cerebras_key),
    }

@router.post("")
async def set_key(
    request: SetKeyRequest,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token=token, db=db)
    
    # Encrypt the API key before storing
    encrypted_key = encrypt(request.api_key)
    
    if request.provider == "openai":
        user.openai_key = encrypted_key
    elif request.provider == "anthropic":
        user.anthropic_key = encrypted_key
    elif request.provider == "gemini":
        user.gemini_key = encrypted_key
    elif request.provider == "cerebras":
        user.cerebras_key = encrypted_key
    else:
        raise HTTPException(status_code=400, detail="Unknown provider")
    
    await db.commit()
    return {"success": True, "provider": request.provider}

@router.delete("/{provider}")
async def delete_key(
    provider: str,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token=token, db=db)
    
    if provider == "openai":
        user.openai_key = None
    elif provider == "anthropic":
        user.anthropic_key = None
    elif provider == "gemini":
        user.gemini_key = None
    elif provider == "cerebras":
        user.cerebras_key = None
    else:
        raise HTTPException(status_code=400, detail="Unknown provider")
    
    await db.commit()
    return {"success": True}
