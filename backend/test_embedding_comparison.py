#!/usr/bin/env python3
"""
Embedding Model Comparison Test Script.

Compares chunking and retrieval quality across three embedding providers:
- Local: sentence-transformers/all-MiniLM-L6-v2
- OpenAI: text-embedding-3-large
- Gemini: text-embedding-004

Evaluates using RAGAS-style metrics (self-contained implementation).

Usage:
    cd backend
    source venv/bin/activate
    python test_embedding_comparison.py
"""

import asyncio
import json
import os
import sys
import time
import re
import statistics
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass, field

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

import chromadb
from chromadb.config import Settings as ChromaSettings
from sqlalchemy import create_engine, text
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


# =============================================================================
# EMBEDDING PROVIDERS (Self-contained)
# =============================================================================

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


class EmbeddingProvider:
    """Base class for embedding providers."""
    
    def __init__(self, provider: str):
        self.provider = provider
        self.config = PROVIDER_CONFIGS[provider]
    
    def embed_text(self, text: str) -> List[float]:
        raise NotImplementedError
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError
    
    @property
    def dimension(self) -> int:
        return self.config['dimension']
    
    @property
    def model_name(self) -> str:
        return self.config['model']


class LocalEmbedding(EmbeddingProvider):
    """Local sentence-transformers embedding."""
    
    def __init__(self):
        super().__init__("local")
        from sentence_transformers import SentenceTransformer
        print(f"Loading local model: {self.config['model']}")
        self._model = SentenceTransformer(self.config['model'], device="cpu")
        print("Local model loaded successfully")
    
    def embed_text(self, text: str) -> List[float]:
        return self._model.encode(text, convert_to_numpy=True).tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts, convert_to_numpy=True, show_progress_bar=True).tolist()


class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI text-embedding-3-large."""
    
    def __init__(self):
        super().__init__("openai")
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self._client = OpenAI(api_key=api_key)
        print(f"OpenAI client initialized: {self.config['model']}")
    
    def embed_text(self, text: str) -> List[float]:
        response = self._client.embeddings.create(model=self.config['model'], input=text)
        return response.data[0].embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        all_embeddings = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self._client.embeddings.create(model=self.config['model'], input=batch)
            batch_embeddings = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([e.embedding for e in batch_embeddings])
        return all_embeddings


class GeminiEmbedding(EmbeddingProvider):
    """Gemini text-embedding-004."""
    
    def __init__(self):
        super().__init__("gemini")
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        genai.configure(api_key=api_key)
        self._client = genai
        print(f"Gemini client initialized: {self.config['model']}")
    
    def embed_text(self, text: str) -> List[float]:
        result = self._client.embed_content(
            model=self.config['model'],
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        all_embeddings = []
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


def get_embedding_provider(provider: str) -> EmbeddingProvider:
    """Factory function to get embedding provider."""
    if provider == "local":
        return LocalEmbedding()
    elif provider == "openai":
        return OpenAIEmbedding()
    elif provider == "gemini":
        return GeminiEmbedding()
    raise ValueError(f"Unknown provider: {provider}")


# =============================================================================
# RAGAS-STYLE EVALUATOR (Self-contained)
# =============================================================================

class RAGEvaluator:
    """RAGAS-style evaluation for RAG quality."""
    
    def __init__(self, llm: ChatOpenAI = None):
        self.llm = llm
    
    async def evaluate(self, question: str, answer: str, contexts: List[str]) -> Dict[str, float]:
        """Evaluate RAG response quality."""
        if not self.llm:
            return {"error": "LLM not configured"}
        
        # Run evaluations in parallel
        faithfulness, relevancy, precision = await asyncio.gather(
            self._eval_faithfulness(answer, contexts),
            self._eval_relevancy(question, answer),
            self._eval_context_precision(question, contexts)
        )
        
        scores = [s for s in [faithfulness, relevancy, precision] if s is not None]
        overall = statistics.mean(scores) if scores else None
        
        return {
            "faithfulness": faithfulness,
            "answer_relevancy": relevancy,
            "context_precision": precision,
            "overall_score": overall
        }
    
    async def _eval_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """Check if answer is grounded in context."""
        if not contexts:
            return 0.0
        
        context_text = "\n".join(contexts[:5])
        prompt = f"""Evaluate if this answer is factually grounded in the context.

CONTEXT:
{context_text}

ANSWER:
{answer}

SCORING (return ONLY the number):
- 1.0: All facts in answer come from context
- 0.7: Most facts are grounded, minor issues
- 0.5: Some facts grounded, some missing
- 0.0: Answer contradicts or invents facts

Return ONLY a number (0.0, 0.5, 0.7, or 1.0):"""

        try:
            response = await self.llm.ainvoke(prompt)
            return self._extract_score(response.content)
        except:
            return 0.5
    
    async def _eval_relevancy(self, question: str, answer: str) -> float:
        """Check if answer addresses the question."""
        prompt = f"""Evaluate if this answer addresses the question.

QUESTION: {question}
ANSWER: {answer}

SCORING (return ONLY the number):
- 1.0: Answer directly and completely addresses question
- 0.7: Answer mostly addresses question
- 0.5: Answer partially related but incomplete
- 0.0: Answer doesn't address question

Return ONLY a number (0.0, 0.5, 0.7, or 1.0):"""

        try:
            response = await self.llm.ainvoke(prompt)
            return self._extract_score(response.content)
        except:
            return 0.5
    
    async def _eval_context_precision(self, question: str, contexts: List[str]) -> float:
        """Check if retrieved contexts are relevant."""
        if not contexts:
            return 0.0
        
        context_text = "\n---\n".join(contexts[:5])
        prompt = f"""Evaluate if these retrieved documents are relevant to the question.

QUESTION: {question}

DOCUMENTS:
{context_text}

SCORING (return ONLY the number):
- 1.0: Documents contain exactly the info needed
- 0.7: Documents relevant but with some noise
- 0.5: Documents somewhat related
- 0.0: Documents irrelevant

Return ONLY a number (0.0, 0.5, 0.7, or 1.0):"""

        try:
            response = await self.llm.ainvoke(prompt)
            return self._extract_score(response.content)
        except:
            return 0.5
    
    def _extract_score(self, text: str) -> float:
        """Extract float score from LLM response."""
        try:
            match = re.search(r"(0\.\d+|0|1\.0|1)", text.strip())
            if match:
                return min(1.0, max(0.0, float(match.group(1))))
            return 0.5
        except:
            return 0.5


# =============================================================================
# TEST QUERIES
# =============================================================================

TEST_QUERIES = [
    "What are my top spending categories?",
    "How much did I spend at restaurants?",
    "What are my recurring subscriptions?",
    "What was my largest single purchase?",
    "How much did I spend in total?",
    "What merchants do I visit most frequently?",
    "How much do I spend on groceries?",
]


# =============================================================================
# RESULT STRUCTURES
# =============================================================================

@dataclass
class ProviderResult:
    """Results for a single embedding provider."""
    provider: str
    model: str
    dimension: int
    embedding_time_ms: float
    retrieval_time_ms: float
    query_results: List[Dict[str, Any]] = field(default_factory=list)
    avg_faithfulness: Optional[float] = None
    avg_answer_relevancy: Optional[float] = None
    avg_context_precision: Optional[float] = None
    avg_overall: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "dimension": self.dimension,
            "embedding_time_ms": round(self.embedding_time_ms, 2),
            "retrieval_time_ms": round(self.retrieval_time_ms, 2),
            "ragas_scores": {
                "faithfulness": self.avg_faithfulness,
                "answer_relevancy": self.avg_answer_relevancy,
                "context_precision": self.avg_context_precision,
                "overall": self.avg_overall
            },
            "query_count": len(self.query_results)
        }


# =============================================================================
# MAIN TEST CLASS
# =============================================================================

class EmbeddingComparisonTest:
    """Main test class for comparing embedding providers."""
    
    def __init__(self, max_transactions: int = 100):
        self.max_transactions = max_transactions
        self.transactions: List[Dict[str, Any]] = []
        self.results: Dict[str, ProviderResult] = {}
        
        # Initialize LLM for answer generation and evaluation
        self.llm = None
        if os.getenv("OPENAI_API_KEY"):
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=os.getenv("OPENAI_API_KEY")
            )
        
        self.evaluator = RAGEvaluator(self.llm)
        self.temp_chroma_dir = Path(__file__).parent / "data" / "temp_comparison_chromadb"
    
    def load_transactions(self) -> int:
        """Load transactions from SQLite database."""
        db_path = Path(__file__).parent / "data" / "finance.db"
        
        if not db_path.exists():
            print(f"❌ Database not found at {db_path}")
            return 0
        
        engine = create_engine(f"sqlite:///{db_path}")
        
        query = text("""
            SELECT id, transaction_date, merchant, amount, category, subcategory, description
            FROM transactions
            ORDER BY transaction_date DESC
            LIMIT :limit
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"limit": self.max_transactions})
            rows = result.fetchall()
        
        self.transactions = []
        for row in rows:
            self.transactions.append({
                "id": row[0],
                "transaction_date": row[1],
                "merchant": row[2],
                "amount": float(row[3]) if row[3] else 0.0,
                "category": row[4],
                "subcategory": row[5],
                "description": row[6]
            })
        
        print(f"✅ Loaded {len(self.transactions)} transactions")
        return len(self.transactions)
    
    def create_transaction_text(self, trans: dict) -> str:
        """Create text representation of transaction."""
        parts = []
        if trans.get('transaction_date'):
            parts.append(f"On {trans['transaction_date']}")
        if trans.get('amount'):
            parts.append(f"spent ${abs(trans['amount']):.2f}")
        if trans.get('merchant'):
            parts.append(f"at {trans['merchant']}")
        if trans.get('category'):
            parts.append(f"for {trans['category']}")
        return " ".join(parts)
    
    def _create_collection(self, provider: str) -> chromadb.Collection:
        """Create isolated ChromaDB collection for a provider."""
        provider_dir = self.temp_chroma_dir / provider
        provider_dir.mkdir(parents=True, exist_ok=True)
        
        client = chromadb.PersistentClient(
            path=str(provider_dir),
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
        )
        
        try:
            client.delete_collection(f"comparison_{provider}")
        except:
            pass
        
        return client.create_collection(name=f"comparison_{provider}", metadata={"provider": provider})
    
    async def test_provider(self, provider: str) -> ProviderResult:
        """Test a single embedding provider."""
        print(f"\n{'='*60}")
        print(f"Testing Provider: {provider.upper()}")
        print(f"{'='*60}")
        
        config = PROVIDER_CONFIGS[provider]
        
        try:
            # Initialize embedding service
            print(f"🔄 Initializing {provider} embedding service...")
            embedding = get_embedding_provider(provider)
            
            # Create isolated collection
            collection = self._create_collection(provider)
            
            # Prepare transaction texts
            texts = []
            metadatas = []
            ids = []
            
            for trans in self.transactions:
                text = self.create_transaction_text(trans)
                texts.append(text)
                metadatas.append({
                    "transaction_id": str(trans['id']),
                    "date": str(trans['transaction_date']),
                    "merchant": str(trans.get('merchant') or ""),
                    "amount": float(trans.get('amount') or 0),
                    "category": str(trans.get('category') or "Uncategorized")
                })
                ids.append(str(trans['id']))
            
            # Generate embeddings with timing
            print(f"🔄 Generating embeddings for {len(texts)} documents...")
            embed_start = time.perf_counter()
            embeddings = embedding.embed_batch(texts)
            embed_time = (time.perf_counter() - embed_start) * 1000
            print(f"✅ Embeddings generated in {embed_time:.2f}ms")
            
            # Add to collection
            collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
            print(f"✅ Added {collection.count()} documents to collection")
            
            # Test retrieval with queries
            query_results = []
            total_retrieval_time = 0
            
            for query in TEST_QUERIES:
                print(f"🔍 Query: {query[:50]}...")
                
                # Generate query embedding and search
                query_start = time.perf_counter()
                query_embedding = embedding.embed_text(query)
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=10,
                    include=["documents", "metadatas", "distances"]
                )
                retrieval_time = (time.perf_counter() - query_start) * 1000
                total_retrieval_time += retrieval_time
                
                # Get contexts
                contexts = results['documents'][0] if results['documents'] else []
                
                # Generate answer
                answer = await self._generate_answer(query, contexts)
                
                # Evaluate
                ragas = await self.evaluator.evaluate(query, answer, contexts)
                
                query_results.append({
                    "query": query,
                    "answer": answer[:200] + "..." if len(answer) > 200 else answer,
                    "context_count": len(contexts),
                    "retrieval_time_ms": retrieval_time,
                    "ragas": ragas
                })
            
            # Aggregate results
            avg_retrieval = total_retrieval_time / len(TEST_QUERIES)
            
            faith_scores = [r['ragas']['faithfulness'] for r in query_results if r['ragas'].get('faithfulness')]
            rel_scores = [r['ragas']['answer_relevancy'] for r in query_results if r['ragas'].get('answer_relevancy')]
            prec_scores = [r['ragas']['context_precision'] for r in query_results if r['ragas'].get('context_precision')]
            overall_scores = [r['ragas']['overall_score'] for r in query_results if r['ragas'].get('overall_score')]
            
            result = ProviderResult(
                provider=provider,
                model=config['model'],
                dimension=config['dimension'],
                embedding_time_ms=embed_time,
                retrieval_time_ms=avg_retrieval,
                query_results=query_results,
                avg_faithfulness=statistics.mean(faith_scores) if faith_scores else None,
                avg_answer_relevancy=statistics.mean(rel_scores) if rel_scores else None,
                avg_context_precision=statistics.mean(prec_scores) if prec_scores else None,
                avg_overall=statistics.mean(overall_scores) if overall_scores else None
            )
            
            print(f"\n📊 {provider.upper()} Results:")
            print(f"   Embedding time: {embed_time:.2f}ms")
            print(f"   Avg retrieval time: {avg_retrieval:.2f}ms")
            print(f"   RAGAS Scores:")
            if result.avg_faithfulness: print(f"     - Faithfulness: {result.avg_faithfulness:.2f}")
            if result.avg_answer_relevancy: print(f"     - Relevancy: {result.avg_answer_relevancy:.2f}")
            if result.avg_context_precision: print(f"     - Precision: {result.avg_context_precision:.2f}")
            if result.avg_overall: print(f"     - Overall: {result.avg_overall:.2f}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error testing {provider}: {e}")
            import traceback
            traceback.print_exc()
            return ProviderResult(
                provider=provider,
                model=config['model'],
                dimension=config['dimension'],
                embedding_time_ms=0,
                retrieval_time_ms=0
            )
    
    async def _generate_answer(self, question: str, contexts: List[str]) -> str:
        """Generate answer using LLM."""
        if not self.llm or not contexts:
            return "No relevant data found."
        
        context_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(contexts[:5])])
        prompt = f"""Based on the following transaction data, answer the question concisely:

TRANSACTION DATA:
{context_text}

QUESTION: {question}

Provide an accurate answer based on the data."""

        try:
            response = await self.llm.ainvoke(prompt)
            return response.content
        except Exception as e:
            return f"Error: {e}"
    
    async def run_comparison(self, providers: List[str] = None) -> Dict[str, ProviderResult]:
        """Run comparison across all specified providers."""
        if providers is None:
            providers = ["local", "openai", "gemini"]
        
        print("\n" + "="*70)
        print("          EMBEDDING MODEL COMPARISON TEST")
        print("="*70)
        print(f"Providers: {', '.join(providers)}")
        print(f"Test queries: {len(TEST_QUERIES)}")
        print(f"Max transactions: {self.max_transactions}")
        
        if not self.load_transactions():
            print("❌ No transactions loaded. Aborting.")
            return {}
        
        for provider in providers:
            try:
                result = await self.test_provider(provider)
                self.results[provider] = result
            except Exception as e:
                print(f"❌ Failed to test {provider}: {e}")
        
        return self.results
    
    def print_comparison_table(self):
        """Print formatted comparison table."""
        if not self.results:
            print("No results to display.")
            return
        
        print("\n" + "="*80)
        print("                    COMPARISON RESULTS SUMMARY")
        print("="*80)
        
        print(f"\n{'Provider':<12} | {'Model':<35} | {'Dim':<6} | {'Embed(ms)':<10}")
        print("-"*75)
        for provider, result in self.results.items():
            print(f"{result.provider:<12} | {result.model:<35} | {result.dimension:<6} | {result.embedding_time_ms:<10.2f}")
        
        print("\n" + "-"*75)
        print(f"{'Provider':<12} | {'Faithful':<10} | {'Relevancy':<10} | {'Precision':<10} | {'Overall':<10}")
        print("-"*75)
        for provider, result in self.results.items():
            faith = f"{result.avg_faithfulness:.2f}" if result.avg_faithfulness else "N/A"
            rel = f"{result.avg_answer_relevancy:.2f}" if result.avg_answer_relevancy else "N/A"
            prec = f"{result.avg_context_precision:.2f}" if result.avg_context_precision else "N/A"
            overall = f"{result.avg_overall:.2f}" if result.avg_overall else "N/A"
            print(f"{result.provider:<12} | {faith:<10} | {rel:<10} | {prec:<10} | {overall:<10}")
        
        print("="*80)
    
    def save_results(self, output_path: str = None):
        """Save results to JSON file."""
        if output_path is None:
            output_path = Path(__file__).parent / "data" / "embedding_comparison_results.json"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        output = {
            "timestamp": datetime.now().isoformat(),
            "test_config": {
                "max_transactions": self.max_transactions,
                "num_queries": len(TEST_QUERIES),
                "queries": TEST_QUERIES
            },
            "results": {k: v.to_dict() for k, v in self.results.items()}
        }
        
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✅ Results saved to: {output_path}")


async def main():
    """Main entry point."""
    print("🔑 Checking API keys...")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    providers_to_test = ["local"]
    
    if openai_key:
        print("   ✅ OPENAI_API_KEY found")
        providers_to_test.append("openai")
    else:
        print("   ⚠️  OPENAI_API_KEY not found - skipping OpenAI")
    
    if gemini_key:
        print("   ✅ GEMINI_API_KEY found")
        providers_to_test.append("gemini")
    else:
        print("   ⚠️  GEMINI_API_KEY not found - skipping Gemini")
    
    if not openai_key:
        print("\n⚠️  Warning: Without OPENAI_API_KEY, RAGAS evaluation won't work.")
    
    test = EmbeddingComparisonTest(max_transactions=100)
    await test.run_comparison(providers_to_test)
    test.print_comparison_table()
    test.save_results()
    
    print("\n✅ Comparison complete!")


if __name__ == "__main__":
    asyncio.run(main())
