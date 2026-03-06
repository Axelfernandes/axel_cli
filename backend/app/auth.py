import os
import httpx
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from jose import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

from .database import get_db
from .models import User

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except:
        return None

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_CALLBACK_URL = os.getenv("GITHUB_CALLBACK_URL")
FRONTEND_URL = os.getenv("FRONTEND_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "default-secret-change-me")

async def get_current_user(
    token: str,
    db: AsyncSession = Depends(get_db)
) -> User:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")

@router.post("/register")
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        email=user_in.email,
        hashed_password=pwd_context.hash(user_in.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/login")
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalar_one_or_none()
    
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not pwd_context.verify(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/github")
async def github_login(token: Optional[str] = None):
    scope = "repo,user,read:org"
    state = token if token else ""
    url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri={GITHUB_CALLBACK_URL}&scope={scope}&state={state}"
    return RedirectResponse(url)

@router.get("/callback")
async def github_callback(code: str, state: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        access_token = token_response.json().get("access_token")
        if not access_token:
            print(f"DEBUG: GitHub Token Response: {token_response.json()}")
            raise HTTPException(status_code=400, detail="No access token received")
        
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        user_data = user_response.json()
        github_id = str(user_data["id"])
        
        # Check if we are linking to an existing user (passed via state as JWT)
        current_user = None
        if state:
            try:
                payload = jwt.decode(state, JWT_SECRET, algorithms=["HS256"])
                user_id = payload.get("sub")
                result = await db.execute(select(User).where(User.id == user_id))
                current_user = result.scalar_one_or_none()
            except:
                pass

        if current_user:
            # Link GitHub to current user
            current_user.github_id = github_id
            current_user.github_username = user_data["login"]
            current_user.github_token = access_token
            user = current_user
        else:
            # Traditional OAuth Login
            result = await db.execute(select(User).where(User.github_id == github_id))
            user = result.scalar_one_or_none()
            
            if not user:
                # Create new user for GitHub login
                user = User(
                    github_id=github_id,
                    github_username=user_data["login"],
                    github_token=access_token,
                )
                db.add(user)
            else:
                user.github_token = access_token
        
        await db.commit()
        
        token = create_access_token({"sub": user.id})
        
    return RedirectResponse(f"{FRONTEND_URL}/dashboard?token={token}")

@router.get("/me")
async def get_me(token: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "email": user.email,
        "github_username": user.github_username,
        "is_github_connected": bool(user.github_token),
        "has_openai_key": bool(user.openai_key),
        "has_anthropic_key": bool(user.anthropic_key),
        "has_gemini_key": bool(user.gemini_key),
        "has_cerebras_key": bool(user.cerebras_key),
    }
