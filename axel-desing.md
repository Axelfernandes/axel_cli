To build **Axel** on the **Vertex–Mistral partner integration**, treat Codestral as “just another model” behind a stable interface so you can switch models later by config only.[1][2][3][4]

***

## 1. Overall design for Axel

- **Axel CLI** (local):
  - Python script (`axel`) that talks to your backend over HTTPS.
- **Axel backend on GCP (Cloud Run)**:
  - FastAPI/Flask app exposing:
    - `POST /chat` – for coding chat, review, explanations.
    - `POST /fim` – for fill‑in‑the‑middle completions (Codestral sweet spot).[5][1]
- **Model layer**:
  - Uses **`MistralGoogleCloud`** client from `mistralai_gcp` to call Codestral on Vertex AI.[4][6][7]
  - Backend logic only depends on an abstract `BaseModelClient`, not directly on Codestral.

When you want to change the model (e.g., Codestral 25.01 → Codestral 2, or even another Mistral model), you only change a model name in config.[3][1][5]

***

## 2. GCP & Mistral-on-Vertex setup

1. **GCP project & Vertex partner models**
   - Create/select a GCP project and enable Vertex AI.[2][1]
   - Mistral models (including Codestral / Codestral 2) are exposed as **partner models** in Vertex AI Model Garden.[1][2][3]

2. **Mistral GCP SDK**
   - Use `mistralai_gcp` (`MistralGoogleCloud`) to call Codestral via Vertex.[6][7][4]
   - Example pattern from docs:

```python
import os
from mistralai_gcp import MistralGoogleCloud

region = os.environ["GOOGLE_CLOUD_REGION"]
project_id = os.environ["GOOGLE_CLOUD_PROJECT_ID"]

client = MistralGoogleCloud(region=region, project_id=project_id)
resp = client.fim.complete(
    model="codestral-2405",
    prompt="def count_words_in_file(file_path: str) -> int:",
    suffix="return n_words",
)
print(resp.choices[0].message.content)
```



***

## 3. Backend abstractions (so models can change)

Define a **model-agnostic interface**:

```python
# app/model_client.py
from typing import List, Dict

class BaseModelClient:
    def chat(self, messages: List[Dict], **kwargs) -> str:
        raise NotImplementedError

    def fim(self, prompt: str, suffix: str, **kwargs) -> str:
        raise NotImplementedError
```

Implement the **Vertex–Mistral** version:

```python
# app/vertex_mistral_client.py
import os
from mistralai_gcp import MistralGoogleCloud  # from mistralai_gcp
from .model_client import BaseModelClient

class VertexMistralClient(BaseModelClient):
    def __init__(self, model_name: str, model_version: str):
        region = os.environ["GOOGLE_CLOUD_REGION"]
        project_id = os.environ["GOOGLE_CLOUD_PROJECT_ID"]
        self.client = MistralGoogleCloud(region=region, project_id=project_id)
        # e.g. model_name="codestral", model_version="2405"
        self.model = f"{model_name}-{model_version}"

    def chat(self, messages, **kwargs) -> str:
        resp = self.client.chat.complete(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        return resp.choices[0].message.content  # per Mistral GCP docs [web:22][web:34]

    def fim(self, prompt: str, suffix: str, **kwargs) -> str:
        resp = self.client.fim.complete(
            model=self.model,
            prompt=prompt,
            suffix=suffix,
            **kwargs,
        )
        return resp.choices[0].message.content  # FIM completion [web:22][web:37]
```

Change model tomorrow by editing env/config:

- Today: `VERTEX_MODEL_NAME=codestral`, `VERTEX_MODEL_VERSION=2405`.[4]
- Tomorrow: `VERTEX_MODEL_NAME=codestral-2`, `VERTEX_MODEL_VERSION=2501` (or whatever the card says).[8][3][5]

No code changes required in the agent logic or CLI.

***

## 4. Axel backend (Cloud Run) API

FastAPI sketch:

```python
# app/main.py
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
```

- Containerize this and deploy to Cloud Run.[9]
- Use a service account with permissions for Vertex AI partner models.[3][1]

***

## 5. Axel CLI (local)

Minimal flow:

1. **Config file**

`~/.axel/config.yaml`:

```yaml
backend_url: https://axel-xxxx.a.run.app
temperature: 0.2
max_tokens: 512
```

2. **Commands**

- `axel chat`:
  - Reads your question and relevant file snippets.
  - Sends:

```json
POST /chat
{
  "messages": [
    {"role": "system", "content": "You are Axel, a coding assistant..."},
    {"role": "user", "content": "Explain this code:\n<file content>"}
  ],
  "options": {"temperature": 0.2}
}
```

- `axel fim`:
  - Supports inline completion: `before` (prompt) and `after` (suffix).
  - Sends to `/fim` with `prompt` and `suffix`.[5][1]

You only hit your backend; you never talk to Vertex directly from the CLI, which keeps the swap logic entirely server-side.

***

## 6. Making model swaps safe and easy

To ensure Axel doesn’t break when you swap models on GCP:

- **Use logical model names**:
  - Map `codestral_default` → `"codestral-2405"` today, `"codestral-25xx"` tomorrow via env or YAML, never hard-code the full ID.[3][4][5]

- **Keep a stable message schema**:
  - Always use the `{"role": "user"/"assistant", "content": ...}` pattern that Mistral on Vertex expects.[1][4]

- **Centralize config**:
  - Only `VertexMistralClient` reads `VERTEX_MODEL_NAME` and `VERTEX_MODEL_VERSION`; Axel logic and CLI remain untouched.[4]

- **Simple smoke tests**:
  - Have a tiny script in the repo that:
    - Calls `chat` with “write a Python function that adds two numbers”.
    - Calls `fim` on a small snippet.
  - Run it whenever you change the model env vars to verify responses.  

***

## 7. Suggested repo scaffold

```text
axel/
  backend/
    app/
      __init__.py
      main.py               # FastAPI app
      model_client.py       # BaseModelClient
      vertex_mistral_client.py
    requirements.txt        # fastapi, uvicorn, mistralai_gcp, pydantic
    Dockerfile
  cli/
    axel/
      __init__.py
      main.py               # Typer/argparse CLI
    pyproject.toml / setup.cfg
```

Next step, if you want, I can outline the exact `Dockerfile` and a minimal `axel chat` CLI script that hits `/chat`, so you can `git init`, fill in, and deploy in one evening.

Sources
[1] Mistral AI models | Generative AI on Vertex AI https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/mistral
[2] Codestral and Mistral Large V2 on Vertex AI https://cloud.google.com/blog/products/ai-machine-learning/codestral-and-mistral-large-v2-on-vertex-ai
[3] Announcing Mistral AI's Mistral Large 24.11 and Codestral ... https://cloud.google.com/blog/products/ai-machine-learning/announcing-new-mistral-large-model-on-vertex-ai
[4] Vertex AI | Mistral Docs https://docs.mistral.ai/deployment/cloud/vertex
[5] Codestral 2 | Generative AI on Vertex AI https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/mistral/codestral-2
[6] mistralai/mistralai-gcp https://www.npmjs.com/package/@mistralai/mistralai-gcp?activeTab=readme
[7] client-python/packages/mistralai_gcp/README.md at main https://github.com/mistralai/client-python/blob/main/packages/mistralai_gcp/README.md
[8] Codestral 25.01 https://mistral.ai/news/codestral-2501
[9] Running Mistral 7B on Google Cloud Run as Serverless API https://www.reddit.com/r/cloudcode/comments/1902uqs/running_mistral_7b_on_google_cloud_run_as/
[10] Google's Vertex AI will use Mistral AI's Codestral https://dig.watch/updates/googles-vertex-ai-will-use-mistral-ais-codestral
[11] Mistral's Codestral 25.01: A Guide With VS Code Examples https://www.datacamp.com/tutorial/codestral-25-01
[12] Google's Vertex AI to use Mistral AI's Codestral https://cio.economictimes.indiatimes.com/news/artificial-intelligence/googles-vertex-ai-to-use-mistral-ais-codestral/112003217
[13] client-python/packages/mistralai_gcp/docs/sdks/fim ... https://github.com/mistralai/client-python/blob/main/packages/mistralai_gcp/docs/sdks/fim/README.md
[14] The complete guide to Mistral AI https://datanorth.ai/blog/the-complete-guide-to-mistral-ai
[15] Mistral AI sets code generation benchmark with Codestral ... https://www.developer-tech.com/news/mistral-ai-code-generation-benchmark-codestral-25-01/
[16] Coding | Mistral Docs https://docs.mistral.ai/capabilities/code_generation
