import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self, persist_directory: str = "./chroma_db", api_key: Optional[str] = None):
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Default to OpenAI if key is provided, otherwise can be configured
        if api_key:
            self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name="text-embedding-3-small"
            )
        else:
            # Fallback or placeholder
            self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
            
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

def get_embedding_service(api_key: Optional[str] = None):
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(api_key=api_key)
    return _embedding_service
