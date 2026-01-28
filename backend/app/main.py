import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .vertex_mistral_client import VertexMistralClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatPayload(BaseModel):
    messages: list
    options: dict | None = None

class FimPayload(BaseModel):
    prompt: str
    suffix: str
    options: dict | None = None

app = FastAPI()

# Initialize client lazily or safely
model_client = None

@app.on_event("startup")
async def startup_event():
    global model_client
    try:
        logger.info("Initializing VertexMistralClient...")
        model_client = VertexMistralClient(
            model_name=os.getenv("VERTEX_MODEL_NAME", "codestral"),
            model_version=os.getenv("VERTEX_MODEL_VERSION", "2501"),
        )
        logger.info("VertexMistralClient initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize VertexMistralClient: {e}")
        # We don't raise here to allow the health check to respond, 
        # but actual endpoints will fail.

@app.get("/health")
async def health():
    return {"status": "ok", "client_initialized": model_client is not None}

@app.post("/chat")
async def chat(payload: ChatPayload):
    if not model_client:
        raise HTTPException(status_code=503, detail="Model client not initialized. Check environment variables.")
    try:
        opts = payload.options or {}
        content = model_client.chat(payload.messages, **opts)
        return {"content": content}
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "type": type(e).__name__}
        )

@app.post("/fim")
async def fim(payload: FimPayload):
    if not model_client:
        raise HTTPException(status_code=503, detail="Model client not initialized. Check environment variables.")
    try:
        opts = payload.options or {}
        content = model_client.fim(payload.prompt, payload.suffix, **opts)
        return {"content": content}
    except Exception as e:
        logger.error(f"Fim endpoint error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "type": type(e).__name__}
        )
