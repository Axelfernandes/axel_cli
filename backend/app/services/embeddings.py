import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
import logging

class RestGeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, api_key: str, model_name: str = "models/gemini-embedding-001"):
        self.api_key = api_key
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:batchEmbedContents?key={self.api_key}"
        
        # We need to chunk requests if there are too many, but typically chroma batches them.
        requests = [
            {"model": self.model_name, "content": {"parts": [{"text": text}]}}
            for text in input
        ]
        
        with httpx.Client(timeout=60) as client:
            response = client.post(url, json={"requests": requests})
            if response.status_code != 200:
                raise ValueError(f"Gemini API Error: {response.text}")
            data = response.json()
            return [ans["values"] for ans in data["embeddings"]]

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, persist_directory: str = "./chroma_db", openai_key: Optional[str] = None, gemini_key: Optional[str] = None):
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        if openai_key:
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=openai_key,
                model_name="text-embedding-3-small"
            )
        elif gemini_key:
            self.embedding_fn = RestGeminiEmbeddingFunction(
                api_key=gemini_key,
                model_name="models/gemini-embedding-001"
            )
        else:
            raise ValueError("No valid API key provided for embeddings. Please configure OpenAI or Gemini keys in settings.")
            
        self.collection = self.client.get_or_create_collection(
            name="axel_codebase",
            embedding_function=self.embedding_fn
        )

    def index_files(self, files: List[Dict[str, str]]):
        """
        Expects a list of dicts with 'path' and 'content'.
        """
        documents = []
        metadatas = []
        ids = []
        
        for file in files:
            path = file['path']
            content = file['content']
            
            # Simple chunking by lines for now (Max 2000 chars per chunk)
            chunks = self._chunk_text(content, max_chars=2000)
            
            for i, chunk in enumerate(chunks):
                documents.append(chunk)
                metadatas.append({"path": path, "chunk": i})
                ids.append(f"{path}_{i}")
        
        if documents:
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Indexed {len(documents)} chunks from {len(files)} files.")

    def query(self, text: str, n_results: int = 5) -> List[Dict]:
        results = self.collection.query(
            query_texts=[text],
            n_results=n_results
        )
        
        formatted_results = []
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i]
            })
        return formatted_results

    def _chunk_text(self, text: str, max_chars: int) -> List[str]:
        """Simple recursive character-based chunking."""
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        while text:
            if len(text) <= max_chars:
                chunks.append(text)
                break
            
            # Find last newline within max_chars
            split_idx = text.rfind('\n', 0, max_chars)
            if split_idx == -1:
                split_idx = max_chars
                
            chunks.append(text[:split_idx])
            text = text[split_idx:].lstrip()
            
        return chunks

# Singleton instance
_embedding_service = None

def get_embedding_service(openai_key: Optional[str] = None, gemini_key: Optional[str] = None):
    # In a multi-user environment, we should ideally not use a single global singleton
    # if users have different keys. For now, we recreate the service if it's called
    # with keys so the correct embedding function is used per-request.
    return EmbeddingService(openai_key=openai_key, gemini_key=gemini_key)
