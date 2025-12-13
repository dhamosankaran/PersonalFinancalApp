"""
Document chunking service for RAG.
Splits documents into semantic chunks for better retrieval.
"""

from typing import List, Dict, Any, Optional
import re
from dataclasses import dataclass


@dataclass
class DocumentChunk:
    """Represents a chunk of a document."""
    document_id: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any]
    page_number: Optional[int] = None


class ChunkingService:
    """Service for chunking documents for RAG."""
    
    def __init__(
        self,
        chunk_size: int = 500,  # Target characters per chunk
        chunk_overlap: int = 100,  # Overlap between chunks
        min_chunk_size: int = 100  # Minimum chunk size
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_document(
        self,
        text: str,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Split document text into overlapping chunks.
        
        Args:
            text: Full document text
            document_id: Unique document identifier
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of DocumentChunk objects
        """
        if not text or len(text.strip()) < self.min_chunk_size:
            return []
        
        chunks = []
        metadata = metadata or {}
        
        # Split by paragraphs first
        paragraphs = self._split_into_paragraphs(text)
        
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            # If adding this paragraph exceeds chunk size, save current and start new
            if len(current_chunk) + len(para) > self.chunk_size and current_chunk:
                chunks.append(DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=current_chunk.strip(),
                    metadata={**metadata, "chunk_type": "text"}
                ))
                chunk_index += 1
                
                # Keep overlap from end of current chunk
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                current_chunk = overlap_text + para + "\n\n"
            else:
                current_chunk += para + "\n\n"
        
        # Don't forget the last chunk
        if current_chunk.strip() and len(current_chunk.strip()) >= self.min_chunk_size:
            chunks.append(DocumentChunk(
                document_id=document_id,
                chunk_index=chunk_index,
                content=current_chunk.strip(),
                metadata={**metadata, "chunk_type": "text"}
            ))
        
        return chunks
    
    def chunk_by_page(
        self,
        pages: List[str],
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Create one chunk per page (for PDFs).
        
        Args:
            pages: List of page texts
            document_id: Unique document identifier
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        metadata = metadata or {}
        
        for i, page_text in enumerate(pages):
            if page_text and page_text.strip():
                chunks.append(DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=page_text.strip(),
                    metadata={**metadata, "chunk_type": "page"},
                    page_number=i + 1
                ))
        
        return chunks
    
    def chunk_transactions(
        self,
        transactions: List[Dict[str, Any]],
        document_id: str,
        group_size: int = 10
    ) -> List[DocumentChunk]:
        """
        Group transactions into chunks for better context.
        
        Args:
            transactions: List of transaction dictionaries
            document_id: Source document ID
            group_size: Number of transactions per chunk
            
        Returns:
            List of DocumentChunk objects representing grouped transactions
        """
        chunks = []
        
        for i in range(0, len(transactions), group_size):
            group = transactions[i:i + group_size]
            
            # Create text representation
            text_parts = []
            total_amount = 0.0
            categories = set()
            
            for trans in group:
                amount = float(trans.get('amount', 0))
                total_amount += amount
                if trans.get('category'):
                    categories.add(trans['category'])
                
                text_parts.append(
                    f"- {trans.get('date', 'Unknown date')}: "
                    f"${amount:.2f} at {trans.get('merchant', 'Unknown')}"
                    f"{' (' + trans.get('category') + ')' if trans.get('category') else ''}"
                )
            
            content = "\n".join(text_parts)
            
            chunks.append(DocumentChunk(
                document_id=document_id,
                chunk_index=i // group_size,
                content=content,
                metadata={
                    "chunk_type": "transaction_group",
                    "transaction_count": len(group),
                    "total_amount": total_amount,
                    "categories": list(categories),
                    "start_index": i,
                    "end_index": i + len(group)
                }
            ))
        
        return chunks
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs."""
        # Split on double newlines or multiple newlines
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]


# Global instance
chunking_service = ChunkingService()
