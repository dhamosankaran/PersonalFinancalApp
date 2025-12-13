"""
Vector store service using ChromaDB.
All vector storage is local for privacy.
Instrumented with metrics collection for observability.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
import uuid
import os
import statistics

from config import settings
from .embeddings import embedding_service
from .metrics import metrics_collector, Timer, MetricsCollector


class VectorStoreService:
    """Service for managing ChromaDB vector store."""
    
    def __init__(self):
        """Initialize the vector store."""
        # Ensure directory exists
        os.makedirs(settings.chroma_persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection_name = "financial_transactions"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Financial transaction embeddings"}
        )
    
    async def add_transaction(
        self,
        transaction_id: str,
        transaction_data: Dict[str, Any],
        user_id: str
    ) -> None:
        """
        Add a single transaction to the vector store.
        
        Args:
            transaction_id: Unique transaction ID
            transaction_data: Transaction data dictionary
            user_id: User ID for filtering
        """
        with Timer(
            MetricsCollector.FLOW_VECTOR_STORE,
            "add_transaction",
            metadata={"transaction_id": str(transaction_id)}
        ):
            # Create text representation
            text = embedding_service.create_transaction_text(transaction_data)
            
            # Generate embedding
            embedding = embedding_service.embed_text(text)
            
            # Get transaction date safely
            trans_date = transaction_data.get('transaction_date')
            
            # ChromaDB requires metadata values to be str, int, float, or bool (not None)
            metadata = {
                "user_id": str(user_id),
                "transaction_id": str(transaction_id),
                "date": str(trans_date) if trans_date else "",
                "merchant": str(transaction_data.get('merchant') or ""),
                "category": str(transaction_data.get('category') or "Uncategorized"),
                "subcategory": str(transaction_data.get('subcategory') or ""),
                "amount": float(transaction_data.get('amount') or 0),
                "month": trans_date.month if trans_date and hasattr(trans_date, 'month') else 0,
                "year": trans_date.year if trans_date and hasattr(trans_date, 'year') else 0,
            }
            
            # Add to collection
            self.collection.add(
                ids=[str(transaction_id)],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata]
            )
        
        # Record metrics
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_VECTOR_STORE,
            "vectors_added"
        )
        self._update_vector_count_gauge()
    
    async def add_transactions_batch(
        self,
        transactions: List[Dict[str, Any]],
        user_id: str
    ) -> None:
        """
        Add multiple transactions in batch for efficiency.
        
        Args:
            transactions: List of transaction dictionaries
            user_id: User ID for filtering
        """
        if not transactions:
            return
        
        with Timer(
            MetricsCollector.FLOW_VECTOR_STORE,
            "add_transactions_batch",
            metadata={"batch_size": len(transactions)}
        ):
            ids = []
            documents = []
            metadatas = []
            
            # Prepare data
            for trans in transactions:
                transaction_id = str(trans.get('id') or uuid.uuid4())
                text = embedding_service.create_transaction_text(trans)
                
                # Get transaction date safely
                trans_date = trans.get('transaction_date')
                
                # ChromaDB requires metadata values to be str, int, float, or bool (not None)
                metadata = {
                    "user_id": str(user_id),
                    "transaction_id": transaction_id,
                    "date": str(trans_date) if trans_date else "",
                    "merchant": str(trans.get('merchant') or ""),
                    "category": str(trans.get('category') or "Uncategorized"),
                    "subcategory": str(trans.get('subcategory') or ""),
                    "amount": float(trans.get('amount') or 0),
                    "month": trans_date.month if trans_date and hasattr(trans_date, 'month') else 0,
                    "year": trans_date.year if trans_date and hasattr(trans_date, 'year') else 0,
                }
                
                ids.append(transaction_id)
                documents.append(text)
                metadatas.append(metadata)
            
            # Generate embeddings in batch
            embeddings = embedding_service.embed_batch(documents)
            
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
        
        # Record metrics
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_VECTOR_STORE,
            "vectors_added",
            len(transactions)
        )
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_VECTOR_STORE,
            "batch_operations"
        )
        metrics_collector.add_histogram(
            MetricsCollector.FLOW_VECTOR_STORE,
            "batch_sizes",
            len(transactions)
        )
        self._update_vector_count_gauge()
    
    async def search(
        self,
        query: str,
        user_id: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for similar transactions.
        
        Args:
            query: Search query
            user_id: User ID for filtering
            n_results: Number of results to return
            filters: Optional additional filters
            
        Returns:
            Search results with documents, metadata, and distances
        """
        with Timer(
            MetricsCollector.FLOW_VECTOR_STORE,
            "search",
            metadata={"query_length": len(query), "n_results": n_results}
        ):
            # Generate query embedding
            query_embedding = embedding_service.embed_text(query)
            
            # Build where clause - skip user filter if user_id is None
            where = {}
            if user_id:
                where["user_id"] = str(user_id)
            if filters:
                where.update(filters)
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where if where else None,
                include=["documents", "metadatas", "distances"]
            )
        
        # Record search metrics
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_VECTOR_STORE,
            "searches_performed"
        )
        
        # Record relevance metrics
        if results.get('distances') and results['distances'][0]:
            distances = results['distances'][0]
            avg_distance = statistics.mean(distances)
            avg_relevance = 1 - avg_distance  # Convert distance to similarity
            
            metrics_collector.add_histogram(
                MetricsCollector.FLOW_VECTOR_STORE,
                "search_distances",
                avg_distance
            )
            metrics_collector.add_histogram(
                MetricsCollector.FLOW_VECTOR_STORE,
                "relevance_scores",
                avg_relevance
            )
            metrics_collector.add_histogram(
                MetricsCollector.FLOW_VECTOR_STORE,
                "results_count",
                len(distances)
            )
        
        return results
    
    async def delete_transaction(self, transaction_id: str) -> None:
        """
        Delete a transaction from the vector store.
        
        Args:
            transaction_id: Transaction ID to delete
        """
        with Timer(
            MetricsCollector.FLOW_VECTOR_STORE,
            "delete_transaction"
        ):
            try:
                self.collection.delete(ids=[str(transaction_id)])
                metrics_collector.increment_counter(
                    MetricsCollector.FLOW_VECTOR_STORE,
                    "vectors_deleted"
                )
            except Exception as e:
                print(f"Error deleting transaction from vector store: {e}")
                metrics_collector.record_error(
                    MetricsCollector.FLOW_VECTOR_STORE,
                    "delete_error"
                )
        
        self._update_vector_count_gauge()
    
    async def delete_user_data(self, user_id: str) -> None:
        """
        Delete all data for a user.
        
        Args:
            user_id: User ID
        """
        with Timer(
            MetricsCollector.FLOW_VECTOR_STORE,
            "delete_user_data"
        ):
            try:
                self.collection.delete(where={"user_id": str(user_id)})
                metrics_collector.increment_counter(
                    MetricsCollector.FLOW_VECTOR_STORE,
                    "user_data_deleted"
                )
            except Exception as e:
                print(f"Error deleting user data from vector store: {e}")
                metrics_collector.record_error(
                    MetricsCollector.FLOW_VECTOR_STORE,
                    "delete_error"
                )
        
        self._update_vector_count_gauge()
    
    async def add_category_summaries(
        self,
        transactions: List[Dict[str, Any]],
        user_id: str
    ) -> int:
        """
        Generate and add category summary documents to improve RAG answers
        for aggregate questions like 'top spending categories'.
        
        Args:
            transactions: List of all transaction dictionaries
            user_id: User ID for filtering
            
        Returns:
            Number of summary documents added
        """
        from collections import defaultdict
        
        if not transactions:
            return 0
        
        # Aggregate by category
        category_totals = defaultdict(lambda: {'amount': 0.0, 'count': 0, 'merchants': set()})
        
        for trans in transactions:
            cat = trans.get('category') or 'Uncategorized'
            amount = abs(float(trans.get('amount', 0)))
            merchant = trans.get('merchant', '')
            
            category_totals[cat]['amount'] += amount
            category_totals[cat]['count'] += 1
            if merchant:
                category_totals[cat]['merchants'].add(merchant)
        
        # Delete existing summary documents for this user
        try:
            self.collection.delete(where={
                "$and": [
                    {"user_id": str(user_id)},
                    {"doc_type": "category_summary"}
                ]
            })
        except Exception:
            pass  # May fail if no existing summaries
        
        # Create summary documents
        chunks = []
        
        # Sort categories by amount
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1]['amount'], reverse=True)
        total_spending = sum(c['amount'] for c in category_totals.values())
        
        # 1. Overall category summary
        summary_lines = ["SPENDING SUMMARY BY CATEGORY (Annual Overview):", ""]
        for rank, (cat, data) in enumerate(sorted_categories, 1):
            pct = (data['amount'] / total_spending * 100) if total_spending > 0 else 0
            top_merchants = list(data['merchants'])[:3]
            summary_lines.append(
                f"{rank}. {cat}: ${data['amount']:,.2f} ({pct:.1f}% of total, {data['count']} transactions)"
            )
            if top_merchants:
                summary_lines.append(f"   Top merchants: {', '.join(top_merchants)}")
        
        summary_lines.append(f"\nTotal spending: ${total_spending:,.2f}")
        summary_lines.append(f"Total transactions: {len(transactions)}")
        
        chunks.append({
            'id': f"summary_categories_{user_id}",
            'content': "\n".join(summary_lines),
            'metadata': {
                'doc_type': 'category_summary',
                'summary_type': 'annual_categories',
                'total_amount': total_spending,
                'category_count': len(sorted_categories)
            }
        })
        
        # 2. Top spending categories document
        top_cats = sorted_categories[:10]
        top_content = [
            "TOP SPENDING CATEGORIES:",
            "",
            "Here are the top spending categories ranked by total amount spent:",
            ""
        ]
        for rank, (cat, data) in enumerate(top_cats, 1):
            pct = (data['amount'] / total_spending * 100) if total_spending > 0 else 0
            top_content.append(f"{rank}. {cat}: ${data['amount']:,.2f} ({pct:.1f}%)")
        
        top_content.append(f"\nTotal spending across all categories: ${total_spending:,.2f}")
        
        chunks.append({
            'id': f"summary_top_categories_{user_id}",
            'content': "\n".join(top_content),
            'metadata': {
                'doc_type': 'category_summary',
                'summary_type': 'top_categories',
                'total_amount': total_spending
            }
        })
        
        # Add chunks to vector store
        return await self.add_document_chunks(chunks, user_id)
    
    async def add_document_chunks(
        self,
        chunks: List[Dict[str, Any]],
        user_id: str
    ) -> int:
        """
        Add document chunks to the vector store.
        
        Args:
            chunks: List of chunk dictionaries with 'content' and 'metadata' keys
            user_id: User ID for filtering
            
        Returns:
            Number of chunks added
        """
        if not chunks:
            return 0
        
        with Timer(
            MetricsCollector.FLOW_VECTOR_STORE,
            "add_document_chunks",
            metadata={"chunk_count": len(chunks)}
        ):
            ids = []
            documents = []
            metadatas = []
            
            for chunk in chunks:
                chunk_id = chunk.get('id', str(uuid.uuid4()))
                content = chunk.get('content', '')
                metadata = chunk.get('metadata', {})
                
                # Add user_id to metadata
                metadata['user_id'] = str(user_id)
                metadata['chunk_id'] = chunk_id
                
                ids.append(chunk_id)
                documents.append(content)
                metadatas.append(metadata)
            
            # Generate embeddings in batch
            embeddings = embedding_service.embed_batch(documents)
            
            # Add to collection
            try:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
                added_count = len(ids)
            except Exception as e:
                print(f"Error adding document chunks: {e}")
                metrics_collector.record_error(
                    MetricsCollector.FLOW_VECTOR_STORE,
                    "add_chunks_error"
                )
                return 0
        
        # Record metrics
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_VECTOR_STORE,
            "chunks_added",
            added_count
        )
        self._update_vector_count_gauge()
        
        return added_count
    
    def _update_vector_count_gauge(self):
        """Update the gauge for total vectors stored."""
        try:
            count = self.collection.count()
            metrics_collector.set_gauge(
                MetricsCollector.FLOW_VECTOR_STORE,
                "total_vectors",
                count
            )
        except Exception:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        count = self.collection.count()
        # Update gauge while we're at it
        metrics_collector.set_gauge(
            MetricsCollector.FLOW_VECTOR_STORE,
            "total_vectors",
            count
        )
        
        return {
            "collection_name": self.collection_name,
            "total_documents": count,
            "embedding_dimension": embedding_service.dimension
        }


# Global instance
vector_store = VectorStoreService()

