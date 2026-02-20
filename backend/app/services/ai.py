from typing import List, Dict, Optional
import os
import json

class AIClient:
    async def chat(self, messages: List[Dict], **kwargs) -> Dict:
        raise NotImplementedError
    
    async def chat_stream(self, messages: List[Dict], **kwargs):
        raise NotImplementedError


class OpenAIClient(AIClient):
    def __init__(self, api_key: str):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def chat(self, messages: List[Dict], **kwargs) -> Dict:
        model = kwargs.get("model", "gpt-4o")
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        return {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
    
    async def chat_stream(self, messages: List[Dict], **kwargs):
        model = kwargs.get("model", "gpt-4o")
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
            stream=True,
            stream_options={"include_usage": True}
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield {"content": chunk.choices[0].delta.content}
            if chunk.usage:
                yield {
                    "usage": {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens
                    }
                }


class AnthropicClient(AIClient):
    def __init__(self, api_key: str):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=api_key)
    
    async def chat(self, messages: List[Dict], **kwargs) -> Dict:
        model = kwargs.get("model", "claude-3-5-sonnet-20241022")
        system_message = ""
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                filtered_messages.append(msg)
        
        response = await self.client.messages.create(
            model=model,
            system=system_message,
            messages=filtered_messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        return {
            "content": response.content[0].text,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        }
    
    async def chat_stream(self, messages: List[Dict], **kwargs):
        model = kwargs.get("model", "claude-3-5-sonnet-20241022")
        system_message = ""
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                filtered_messages.append(msg)
        
        async with self.client.messages.stream(
            model=model,
            system=system_message,
            messages=filtered_messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    yield {"content": event.delta.text}
                elif event.type == "message_stop":
                    # Anthropic stream object has usage after consumption
                    final_msg = await stream.get_final_message()
                    yield {
                        "usage": {
                            "prompt_tokens": final_msg.usage.input_tokens,
                            "completion_tokens": final_msg.usage.output_tokens,
                            "total_tokens": final_msg.usage.input_tokens + final_msg.usage.output_tokens
                        }
                    }


class GeminiClient(AIClient):
    """
    Calls the Gemini REST API directly via httpx.
    This avoids SDK compatibility issues with Python 3.8.
    """
    GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _build_contents(self, messages: List[Dict]) -> list:
        """Convert OpenAI-style messages to Gemini content format."""
        contents = []
        system_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            text = msg.get("content", "")
            if role == "system":
                system_parts.append({"text": text})
            else:
                gemini_role = "model" if role == "assistant" else "user"
                contents.append({"role": gemini_role, "parts": [{"text": text}]})
        return contents, system_parts

    async def chat(self, messages: List[Dict], **kwargs) -> Dict:
        import httpx
        model = kwargs.get("model", "gemini-flash-latest")
        contents, system_parts = self._build_contents(messages)
        
        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 4096),
            },
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}

        url = f"{self.GEMINI_API}/{model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            usage = data.get("usageMetadata", {})
            return {
                "content": data["candidates"][0]["content"]["parts"][0]["text"],
                "usage": {
                    "prompt_tokens": usage.get("promptTokenCount", 0),
                    "completion_tokens": usage.get("candidatesTokenCount", 0),
                    "total_tokens": usage.get("totalTokenCount", 0)
                }
            }

    async def chat_stream(self, messages: List[Dict], **kwargs):
        import httpx
        model = kwargs.get("model", "gemini-flash-latest")
        contents, system_parts = self._build_contents(messages)

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", 4096),
            },
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}

        url = f"{self.GEMINI_API}/{model}:streamGenerateContent?alt=sse&key={self.api_key}"
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json as _json
                        try:
                            chunk = _json.loads(line[6:])
                            if "candidates" in chunk:
                                text = chunk["candidates"][0]["content"]["parts"][0]["text"]
                                yield {"content": text}
                            if "usageMetadata" in chunk:
                                usage = chunk["usageMetadata"]
                                yield {
                                    "usage": {
                                        "prompt_tokens": usage.get("promptTokenCount", 0),
                                        "completion_tokens": usage.get("candidatesTokenCount", 0),
                                        "total_tokens": usage.get("totalTokenCount", 0)
                                    }
                                }
                        except Exception:
                            continue


class VertexMistralClient(AIClient):
    def __init__(self, project_id: str, region: str):
        from mistralai_gcp import MistralGoogleCloud
        self.client = MistralGoogleCloud(region=region, project_id=project_id)
        self.model = os.getenv("VERTEX_MODEL_NAME", "codestral")
        self.version = os.getenv("VERTEX_MODEL_VERSION", "2501")
    
    async def chat(self, messages: List[Dict], **kwargs) -> Dict:
        full_model = f"{self.model}-{self.version}"
        response = self.client.chat.complete(
            model=full_model,
            messages=messages,
            **kwargs,
        )
        # Mistral usage
        return {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        }

    async def chat_stream(self, messages: List[Dict], **kwargs):
        """Streaming chat completion for Mistral on Vertex AI."""
        full_model = f"{self.model}-{self.version}"
        # Vertex AI Mistral SDK uses a sync stream generator
        stream_response = self.client.chat.stream(
            model=full_model,
            messages=messages,
            **kwargs,
        )
        for chunk in stream_response:
            if chunk.choices[0].delta.content:
                yield {"content": chunk.choices[0].delta.content}
            if hasattr(chunk, 'usage') and chunk.usage:
                yield {
                    "usage": {
                        "prompt_tokens": chunk.usage.input_tokens,
                        "completion_tokens": chunk.usage.output_tokens,
                        "total_tokens": chunk.usage.input_tokens + chunk.usage.output_tokens
                    }
                }
        # Note: Mistral sync stream might only provide usage at the end or not at all depending on SDK version


class CerebrasClient(AIClient):
    def __init__(self, api_key: str):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.cerebras.ai/v1"
        )
    
    async def chat(self, messages: List[Dict], **kwargs) -> Dict:
        model = kwargs.get("model", "llama3.1-8b")
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        return {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
    
    async def chat_stream(self, messages: List[Dict], **kwargs):
        model = kwargs.get("model", "llama3.1-8b")
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
            stream=True,
            stream_options={"include_usage": True}
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield {"content": chunk.choices[0].delta.content}
            if hasattr(chunk, 'usage') and chunk.usage:
                yield {
                    "usage": {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens
                    }
                }


def get_ai_client(provider: str, api_key: str, **kwargs) -> AIClient:
    if provider == "openai":
        return OpenAIClient(api_key)
    elif provider == "anthropic":
        return AnthropicClient(api_key)
    elif provider == "gemini":
        return GeminiClient(api_key)
    elif provider == "cerebras":
        return CerebrasClient(api_key)
    elif provider == "vertex_mistral":
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        region = os.getenv("GOOGLE_CLOUD_REGION")
        return VertexMistralClient(project_id, region)
    else:
        raise ValueError(f"Unknown provider: {provider}")
