#!/usr/bin/env python3
"""Process a single PDF for testing."""

import sys
import os

# Set up paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
os.chdir('backend')

import asyncio
from services.document_processor import DocumentProcessor
from services.categorizer import Categorizer
from services.vector_store import vector_store
from database import get_db, init_db
from models import Transaction, User, UploadedDocument
from sqlalchemy.orm import Session

async def process_single_pdf(pdf_path: str, user_email: str = "test@example.com"):
    """Process a single PDF and add to vector store."""
    # Convert to absolute path
    if not os.path.isabs(pdf_path):
        pdf_path = os.path.join('..', pdf_path)
    
    print(f"Processing: {pdf_path}")
    print("="*60)
    
    # Initialize
    init_db()
    processor = DocumentProcessor()
    categorizer = Categorizer()
    
    # Get DB session
    db = next(get_db())
    
    # Clear previous test data
    test_user = db.query(User).filter(User.email == user_email).first()
    if test_user:
        db.query(Transaction).filter(Transaction.user_id == test_user.id).delete()
        db.commit()
        await vector_store.delete_user_data(str(test_user.id))
    else:
        test_user = User(email=user_email)
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
    
    # Process PDF
    transactions = await processor.process_pdf(pdf_path)
    print(f"\nExtracted {len(transactions)} transactions")
    
    # Show sample
    for i, t in enumerate(transactions[:10]):
        date_str = t.get('date').strftime('%Y-%m-%d') if t.get('date') else 'N/A'
        print(f"  {i+1}. {date_str} | {t.get('merchant', 'N/A')[:35]:<35} | ${t.get('amount', 0):.2f}")
    if len(transactions) > 10:
        print(f"  ... and {len(transactions) - 10} more")
    
    # Save to database and vector store
    trans_to_add = []
    for t in transactions:
        cat_info = categorizer.categorize(t.get('merchant', ''), t.get('description'))
        
        trans = Transaction(
            user_id=test_user.id,
            transaction_date=t.get('date'),
            merchant=t.get('merchant'),
            amount=t.get('amount'),
            category=cat_info.get('category'),
            subcategory=cat_info.get('subcategory'),
            source_file=os.path.basename(pdf_path)
        )
        db.add(trans)
        trans_to_add.append(trans)
    
    db.commit()
    for t in trans_to_add:
        db.refresh(t)
    
    # Add to vector store
    trans_dict = [
        {
            'id': str(t.id),
            'transaction_date': t.transaction_date,
            'merchant': t.merchant,
            'amount': float(t.amount) if t.amount else 0,
            'category': t.category,
            'subcategory': t.subcategory,
        }
        for t in trans_to_add
    ]
    await vector_store.add_transactions_batch(trans_dict, str(test_user.id))
    
    print(f"\n✅ Added {len(trans_to_add)} transactions to database and vector store")
    print(f"   Vector store count: {vector_store.get_stats()['total_documents']}")
    
    db.close()
    return len(trans_to_add)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_single_pdf.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    asyncio.run(process_single_pdf(pdf_path))
