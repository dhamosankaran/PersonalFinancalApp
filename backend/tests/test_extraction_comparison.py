"""
Test script to compare PDFPlumber vs LLM extraction methods.
"""

import asyncio
import sys
import os

# Add backend to path (parent of tests directory)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from services.document_processor import DocumentProcessor
from services.llm_extractor import LLMExtractor


async def compare_extraction_methods(pdf_path: str):
    """Compare PDFPlumber and LLM extraction for a given PDF."""
    
    print(f"\n{'='*60}")
    print(f"Comparing extraction methods for: {os.path.basename(pdf_path)}")
    print(f"{'='*60}\n")
    
    processor = DocumentProcessor()
    llm_extractor = LLMExtractor()
    
    # Method 1: PDFPlumber
    print("🔧 Extracting with PDFPlumber...")
    try:
        pdfplumber_results = await processor.process_pdf(pdf_path, extraction_method="pdfplumber")
        print(f"   ✅ Found {len(pdfplumber_results)} transactions\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
        pdfplumber_results = []
    
    # Method 2: LLM (Gemini Vision)
    print("🤖 Extracting with Gemini Vision (LLM)...")
    try:
        llm_results = await processor.process_pdf(pdf_path, extraction_method="llm")
        print(f"   ✅ Found {len(llm_results)} transactions\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
        llm_results = []
    
    # Comparison
    print(f"\n{'='*60}")
    print("COMPARISON RESULTS")
    print(f"{'='*60}\n")
    
    print(f"{'Method':<20} {'Transactions':<15} {'Total Amount':<15}")
    print(f"{'-'*50}")
    
    pdfplumber_total = sum(t.get('amount', 0) for t in pdfplumber_results)
    llm_total = sum(t.get('amount', 0) for t in llm_results)
    
    print(f"{'PDFPlumber':<20} {len(pdfplumber_results):<15} ${pdfplumber_total:,.2f}")
    print(f"{'LLM (Gemini)':<20} {len(llm_results):<15} ${llm_total:,.2f}")
    
    diff = len(llm_results) - len(pdfplumber_results)
    if diff > 0:
        print(f"\n📊 LLM found {diff} MORE transactions than PDFPlumber")
    elif diff < 0:
        print(f"\n📊 PDFPlumber found {abs(diff)} MORE transactions than LLM")
    else:
        print(f"\n📊 Both methods found the same number of transactions")
    
    # Sample transactions from each
    print(f"\n{'='*60}")
    print("SAMPLE TRANSACTIONS (First 5)")
    print(f"{'='*60}")
    
    print("\nPDFPlumber:")
    for t in pdfplumber_results[:5]:
        print(f"  {str(t.get('date', 'N/A'))[:10]:12} {t.get('merchant', 'N/A')[:30]:32} ${t.get('amount', 0):>10.2f}")
    
    print("\nLLM (Gemini):")
    for t in llm_results[:5]:
        print(f"  {str(t.get('date', 'N/A'))[:10]:12} {t.get('merchant', 'N/A')[:30]:32} ${t.get('amount', 0):>10.2f}")
    
    return {
        "pdfplumber": {
            "count": len(pdfplumber_results),
            "total": pdfplumber_total,
            "transactions": pdfplumber_results
        },
        "llm": {
            "count": len(llm_results),
            "total": llm_total,
            "transactions": llm_results
        }
    }


if __name__ == "__main__":
    # Default to October 20.pdf if no argument provided
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Try to find statements directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pdf_path = os.path.join(base_dir, "statements", "October 20.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    asyncio.run(compare_extraction_methods(pdf_path))
