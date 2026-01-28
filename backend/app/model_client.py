from typing import List, Dict

class BaseModelClient:
    def chat(self, messages: List[Dict], **kwargs) -> str:
        raise NotImplementedError

    def fim(self, prompt: str, suffix: str, **kwargs) -> str:
        raise NotImplementedError
