import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(".env.cloudrun")

from .database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_client
    await init_db()
    logger.info("Database initialized.")
    yield

app = FastAPI(title="Axel API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3501"),
        "http://localhost:3000",
        "http://localhost:3501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .auth import router as auth_router
from .routers.repos import router as repos_router
from .routers.chat import router as chat_router
from .routers.keys import router as keys_router

app.include_router(auth_router)
app.include_router(repos_router)
app.include_router(chat_router)
app.include_router(keys_router)

class ChatPayload(BaseModel):
    messages: list
    options: dict = None

class FimPayload(BaseModel):
    prompt: str
    suffix: str
    options: dict = None

@app.get("/health")
async def health():
    return {"status": "ok", "client_initialized": False}

@app.post("/chat/legacy")
async def chat(payload: ChatPayload):
    raise HTTPException(status_code=503, detail="Vertex AI not configured for local development")

@app.post("/fim/legacy")
async def fim(payload: FimPayload):
    raise HTTPException(status_code=503, detail="Vertex AI not configured for local development")
