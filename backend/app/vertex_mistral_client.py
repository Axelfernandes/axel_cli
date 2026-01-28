import os
import logging
from mistralai_gcp import MistralGoogleCloud

logger = logging.getLogger(__name__)
from .model_client import BaseModelClient

class VertexMistralClient(BaseModelClient):
    def __init__(self, model_name: str, model_version: str):
        region = os.getenv("GOOGLE_CLOUD_REGION")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        
        if not region or not project_id:
            raise ValueError(f"Missing required environment variables: GOOGLE_CLOUD_REGION={region}, GOOGLE_CLOUD_PROJECT_ID={project_id}")
            
        self.client = MistralGoogleCloud(region=region, project_id=project_id)
        
        # If version is provided, hyphenate it; otherwise use name as is.
        # This allows using names like 'codestral-2' directly.
        if model_version and model_version.strip():
            self.model = f"{model_name}-{model_version}"
        else:
            self.model = model_name

    def chat(self, messages, **kwargs) -> str:
        try:
            resp = self.client.chat.complete(
                model=self.model,
                messages=messages,
                **kwargs,
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise e

    def fim(self, prompt: str, suffix: str, **kwargs) -> str:
        try:
            resp = self.client.fim.complete(
                model=self.model,
                prompt=prompt,
                suffix=suffix,
                **kwargs,
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in fim completion: {e}")
            raise e
