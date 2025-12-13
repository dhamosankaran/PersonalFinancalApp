"""
Embedding service using sentence-transformers.
All embeddings are generated locally for privacy.
Instrumented with metrics collection for observability.
"""

import time
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np

from config import settings
from .metrics import metrics_collector, Timer, MetricsCollector


class EmbeddingService:
    """Service for generating embeddings locally."""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the embedding service."""
        if self._model is None:
            print(f"Loading embedding model: {settings.embedding_model}")
            self._model = SentenceTransformer(
                settings.embedding_model,
                device=settings.embedding_device
            )
            print("Embedding model loaded successfully")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as list of floats
        """
        with Timer(
            MetricsCollector.FLOW_EMBEDDING, 
            "embed_text",
            metadata={"text_length": len(text)}
        ) as timer:
            embedding = self._model.encode(text, convert_to_numpy=True)
            result = embedding.tolist()
        
        # Record additional metrics
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_EMBEDDING, 
            "embeddings_generated"
        )
        metrics_collector.add_histogram(
            MetricsCollector.FLOW_EMBEDDING,
            "text_lengths",
            len(text)
        )
        
        return result
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        total_chars = sum(len(t) for t in texts)
        
        with Timer(
            MetricsCollector.FLOW_EMBEDDING,
            "embed_batch",
            metadata={
                "batch_size": len(texts),
                "total_chars": total_chars
            }
        ) as timer:
            embeddings = self._model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            result = embeddings.tolist()
        
        # Record batch metrics
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_EMBEDDING, 
            "embeddings_generated",
            len(texts)
        )
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_EMBEDDING,
            "batch_operations"
        )
        metrics_collector.add_histogram(
            MetricsCollector.FLOW_EMBEDDING,
            "batch_sizes",
            len(texts)
        )
        
        # Calculate and record tokens/second (approximate)
        if timer.duration_ms and timer.duration_ms > 0:
            chars_per_second = (total_chars / timer.duration_ms) * 1000
            metrics_collector.set_gauge(
                MetricsCollector.FLOW_EMBEDDING,
                "chars_per_second",
                chars_per_second
            )
        
        return result
    
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
    
    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self._model.get_sentence_embedding_dimension()


# Global instance
embedding_service = EmbeddingService()
