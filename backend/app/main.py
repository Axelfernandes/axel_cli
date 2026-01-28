import os
from fastapi import FastAPI
from pydantic import BaseModel
from .vertex_mistral_client import VertexMistralClient

class ChatPayload(BaseModel):
    messages: list
    options: dict | None = None

class FimPayload(BaseModel):
    prompt: str
    suffix: str
    options: dict | None = None

app = FastAPI()

model_client = VertexMistralClient(
    model_name=os.getenv("VERTEX_MODEL_NAME", "codestral"),
    model_version=os.getenv("VERTEX_MODEL_VERSION", "2405"),
)

@app.post("/chat")
async def chat(payload: ChatPayload):
    opts = payload.options or {}
    content = model_client.chat(payload.messages, **opts)
    return {"content": content}

@app.post("/fim")
async def fim(payload: FimPayload):
    opts = payload.options or {}
    content = model_client.fim(payload.prompt, payload.suffix, **opts)
    return {"content": content}
