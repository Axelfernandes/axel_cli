import os
from mistralai_gcp import MistralGoogleCloud
from .model_client import BaseModelClient

class VertexMistralClient(BaseModelClient):
    def __init__(self, model_name: str, model_version: str):
        region = os.getenv("GOOGLE_CLOUD_REGION")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        
        if not region or not project_id:
            raise ValueError(f"Missing required environment variables: GOOGLE_CLOUD_REGION={region}, GOOGLE_CLOUD_PROJECT_ID={project_id}")
            
        self.client = MistralGoogleCloud(region=region, project_id=project_id)
        # e.g. model_name="codestral", model_version="2405"
        self.model = f"{model_name}-{model_version}"

    def chat(self, messages, **kwargs) -> str:
        resp = self.client.chat.complete(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        return resp.choices[0].message.content

    def fim(self, prompt: str, suffix: str, **kwargs) -> str:
        resp = self.client.fim.complete(
            model=self.model,
            prompt=prompt,
            suffix=suffix,
            **kwargs,
        )
        return resp.choices[0].message.content
