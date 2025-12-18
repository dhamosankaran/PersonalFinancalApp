"""
Multi-Provider Embedding Service for Embedding Model Comparison.

Supports three embedding providers:
- local: sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
- openai: text-embedding-3-large (3072 dimensions)
- gemini: gemini-embedding-001 (768 dimensions)
"""

import os
import time
from typing import List, Literal, Optional
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


# Provider type
ProviderType = Literal["local", "openai", "gemini"]

# Provider configurations
PROVIDER_CONFIGS = {
    "local": {
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "dimension": 384,
        "description": "Local sentence-transformers model"
    },
    "openai": {
        "model": "text-embedding-3-large",
        "dimension": 3072,
        "description": "OpenAI's large embedding model"
    },
    "gemini": {
        "model": "models/text-embedding-004",
        "dimension": 768,
        "description": "Google's Gemini embedding model"
    }
}


class MultiEmbeddingService:
    """
    Unified embedding service with switchable backends.
    
    Supports:
    - local: sentence-transformers (offline, fast, 384 dims)
    - openai: text-embedding-3-large (API, high quality, 3072 dims)
    - gemini: text-embedding-004 (API, balanced, 768 dims)
    """
    
    def __init__(self, provider: ProviderType = "local"):
        """
        Initialize embedding service with specified provider.
        
        Args:
            provider: One of 'local', 'openai', 'gemini'
        """
        self.provider = provider
        self.config = PROVIDER_CONFIGS[provider]
        self._client = None
        self._model = None
        
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the selected provider."""
        if self.provider == "local":
            self._init_local()
        elif self.provider == "openai":
            self._init_openai()
        elif self.provider == "gemini":
            self._init_gemini()
    
    def _init_local(self):
        """Initialize local sentence-transformers model."""
        from sentence_transformers import SentenceTransformer
        print(f"Loading local model: {self.config['model']}")
        self._model = SentenceTransformer(
            self.config['model'],
            device="cpu"
        )
        print("Local embedding model loaded successfully")
    
    def _init_openai(self):
        """Initialize OpenAI embedding client."""
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        self._client = OpenAI(api_key=api_key)
        print(f"OpenAI client initialized for model: {self.config['model']}")
    
    def _init_gemini(self):
        """Initialize Gemini embedding client."""
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found in environment")
        genai.configure(api_key=api_key)
        self._client = genai
        print(f"Gemini client initialized for model: {self.config['model']}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
        """
        if self.provider == "local":
            return self._embed_local(text)
        elif self.provider == "openai":
            return self._embed_openai(text)
        elif self.provider == "gemini":
            return self._embed_gemini(text)
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing (local only)
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        if self.provider == "local":
            return self._embed_batch_local(texts, batch_size)
        elif self.provider == "openai":
            return self._embed_batch_openai(texts)
        elif self.provider == "gemini":
            return self._embed_batch_gemini(texts)
    
    # Local embedding methods
    def _embed_local(self, text: str) -> List[float]:
        """Generate embedding using local model."""
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def _embed_batch_local(self, texts: List[str], batch_size: int) -> List[List[float]]:
        """Generate batch embeddings using local model."""
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        return embeddings.tolist()
    
    # OpenAI embedding methods
    def _embed_openai(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        response = self._client.embeddings.create(
            model=self.config['model'],
            input=text
        )
        return response.data[0].embedding
    
    def _embed_batch_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate batch embeddings using OpenAI API."""
        # OpenAI supports up to 2048 inputs per request
        all_embeddings = []
        batch_size = 100  # Safe batch size
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self._client.embeddings.create(
                model=self.config['model'],
                input=batch
            )
            # Sort by index to maintain order
            batch_embeddings = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([e.embedding for e in batch_embeddings])
        
        return all_embeddings
    
    # Gemini embedding methods
    def _embed_gemini(self, text: str) -> List[float]:
        """Generate embedding using Gemini API."""
        result = self._client.embed_content(
            model=self.config['model'],
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    
    def _embed_batch_gemini(self, texts: List[str]) -> List[List[float]]:
        """Generate batch embeddings using Gemini API."""
        # Gemini batch embedding
        all_embeddings = []
        
        # Process in smaller batches to avoid rate limits
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            result = self._client.embed_content(
                model=self.config['model'],
                content=batch,
                task_type="retrieval_document"
            )
            all_embeddings.extend(result['embedding'])
        
        return all_embeddings
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension for current provider."""
        return self.config['dimension']
    
    @property
    def model_name(self) -> str:
        """Get model name for current provider."""
        return self.config['model']
    
    def create_transaction_text(self, transaction: dict) -> str:
        """
        Create a rich text representation of a transaction for embedding.
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            Formatted text string
        """
        parts = []
        
        if transaction.get('transaction_date'):
            parts.append(f"On {transaction['transaction_date']}")
        
        if transaction.get('amount'):
            parts.append(f"spent ${transaction['amount']:.2f}")
        
        if transaction.get('merchant'):
            parts.append(f"at {transaction['merchant']}")
        
        if transaction.get('category'):
            parts.append(f"for {transaction['category']}")
        
        if transaction.get('subcategory'):
            parts.append(f"({transaction['subcategory']})")
        
        if transaction.get('description'):
            parts.append(f"- {transaction['description']}")
        
        return " ".join(parts)


def get_embedding_service(provider: ProviderType = "local") -> MultiEmbeddingService:
    """Factory function to get embedding service for a provider."""
    return MultiEmbeddingService(provider)
