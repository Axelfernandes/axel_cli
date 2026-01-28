import os
from mistralai_gcp import MistralGoogleCloud
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
        return resp.choices[0].message.content

    def fim(self, prompt: str, suffix: str, **kwargs) -> str:
        resp = self.client.fim.complete(
            model=self.model,
            prompt=prompt,
            suffix=suffix,
            **kwargs,
        )
        return resp.choices[0].message.content
