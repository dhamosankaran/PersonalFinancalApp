"""Upload router for handling file uploads."""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from datetime import datetime

from database import get_db
from models import UploadedDocument, Transaction, User
from schemas import UploadedDocumentResponse
from services import DocumentProcessor, Categorizer, vector_store, analytics_service
from config import settings

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Initialize services
document_processor = DocumentProcessor()
categorizer = Categorizer()


@router.post("/", response_model=UploadedDocumentResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_email: str = "default@example.com",  # Simplified auth for now
    db: Session = Depends(get_db)
):
    """
    Upload a PDF or CSV file for processing.
    """
    # Validate file type
    file_extension = file.filename.split('.')[-1].lower()
    if file_extension not in ['pdf', 'csv']:
        raise HTTPException(status_code=400, detail="Only PDF and CSV files are supported")
    
    # Get or create user
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Save file
    os.makedirs(settings.upload_directory, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(settings.upload_directory, f"{file_id}.{file_extension}")
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Create document record
    document = UploadedDocument(
        user_id=user.id,
        filename=file.filename,
        file_type=file_extension,
        processed=False
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Process file in background (for now, do it synchronously)
    try:
        if file_extension == 'pdf':
            extracted_transactions = await document_processor.process_pdf(file_path)
        else:
            extracted_transactions = await document_processor.process_csv(file_path)
        
        # Save transactions
        transactions_to_add = []
        for trans_data in extracted_transactions:
            # Categorize
            category_info = categorizer.categorize(
                trans_data.get('merchant', ''),
                trans_data.get('description')
            )
            
            transaction = Transaction(
                user_id=user.id,
                transaction_date=trans_data.get('date'),
                merchant=trans_data.get('merchant'),
                amount=trans_data.get('amount'),
                category=category_info.get('category'),
                subcategory=category_info.get('subcategory'),
                description=trans_data.get('description'),
                source_file=file.filename
            )
            db.add(transaction)
            transactions_to_add.append(transaction)
        
        db.commit()
        
        # Refresh to get IDs
        for trans in transactions_to_add:
            db.refresh(trans)
        
        # Add to vector store
        transactions_dict = [
            {
                'id': trans.id,
                'transaction_date': trans.transaction_date,
                'merchant': trans.merchant,
                'amount': trans.amount,
                'category': trans.category,
                'subcategory': trans.subcategory,
                'description': trans.description
            }
            for trans in transactions_to_add
        ]
        await vector_store.add_transactions_batch(transactions_dict, str(user.id))
        
        # Sync to analytics DB
        await analytics_service.sync_transactions(transactions_dict)
        
        # Update document
        document.processed = True
        document.transaction_count = len(transactions_to_add)
        db.commit()
        db.refresh(document)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    return document


@router.post("/batch")
async def upload_files_batch(
    files: List[UploadFile] = File(...),
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """
    Upload multiple PDF or CSV files for batch processing.
    Returns detailed results for each file including success/failure status.
    """
    # Get or create user
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    results = {
        "total_files": len(files),
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "total_transactions": 0,
        "files": []
    }
    
    for file in files:
        file_result = {
            "filename": file.filename,
            "status": "pending",
            "transaction_count": 0,
            "error": None
        }
        
        try:
            # Validate file type
            file_extension = file.filename.split('.')[-1].lower()
            if file_extension not in ['pdf', 'csv']:
                file_result["status"] = "failed"
                file_result["error"] = "Only PDF and CSV files are supported"
                results["failed"] += 1
                results["files"].append(file_result)
                continue
            
            # Check if already processed (by filename)
            existing_doc = db.query(UploadedDocument).filter(
                UploadedDocument.user_id == user.id,
                UploadedDocument.filename == file.filename,
                UploadedDocument.processed == True
            ).first()
            
            if existing_doc:
                file_result["status"] = "skipped"
                file_result["transaction_count"] = existing_doc.transaction_count or 0
                file_result["error"] = "Already processed"
                results["skipped"] += 1
                results["files"].append(file_result)
                continue
            
            # Save file
            os.makedirs(settings.upload_directory, exist_ok=True)
            file_id = str(uuid.uuid4())
            file_path = os.path.join(settings.upload_directory, f"{file_id}.{file_extension}")
            
            # Reset file position and read content
            await file.seek(0)
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Create or update document record
            document = db.query(UploadedDocument).filter(
                UploadedDocument.user_id == user.id,
                UploadedDocument.filename == file.filename
            ).first()
            
            if not document:
                document = UploadedDocument(
                    user_id=user.id,
                    filename=file.filename,
                    file_type=file_extension,
                    processed=False
                )
                db.add(document)
                db.commit()
                db.refresh(document)
            
            # Process file
            if file_extension == 'pdf':
                extracted_transactions = await document_processor.process_pdf(file_path)
            else:
                extracted_transactions = await document_processor.process_csv(file_path)
            
            # Save transactions
            transactions_to_add = []
            for trans_data in extracted_transactions:
                category_info = categorizer.categorize(
                    trans_data.get('merchant', ''),
                    trans_data.get('description')
                )
                
                transaction = Transaction(
                    user_id=user.id,
                    transaction_date=trans_data.get('date'),
                    merchant=trans_data.get('merchant'),
                    amount=trans_data.get('amount'),
                    category=category_info.get('category'),
                    subcategory=category_info.get('subcategory'),
                    description=trans_data.get('description'),
                    source_file=file.filename
                )
                db.add(transaction)
                transactions_to_add.append(transaction)
            
            db.commit()
            
            # Refresh to get IDs
            for trans in transactions_to_add:
                db.refresh(trans)
            
            # Add to vector store
            transactions_dict = [
                {
                    'id': trans.id,
                    'transaction_date': trans.transaction_date,
                    'merchant': trans.merchant,
                    'amount': trans.amount,
                    'category': trans.category,
                    'subcategory': trans.subcategory,
                    'description': trans.description
                }
                for trans in transactions_to_add
            ]
            await vector_store.add_transactions_batch(transactions_dict, str(user.id))
            
            # Sync to analytics DB
            await analytics_service.sync_transactions(transactions_dict)
            
            # Update document
            document.processed = True
            document.transaction_count = len(transactions_to_add)
            db.commit()
            
            file_result["status"] = "processed"
            file_result["transaction_count"] = len(transactions_to_add)
            results["processed"] += 1
            results["total_transactions"] += len(transactions_to_add)
            
        except Exception as e:
            file_result["status"] = "failed"
            file_result["error"] = str(e)
            results["failed"] += 1
        
        results["files"].append(file_result)
    
    return results


@router.get("/documents", response_model=List[UploadedDocumentResponse])
async def list_documents(
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """Get list of uploaded documents."""
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        return []
    
    documents = db.query(UploadedDocument).filter(
        UploadedDocument.user_id == user.id
    ).order_by(UploadedDocument.uploaded_at.desc()).all()
    
    return documents


@router.post("/load-statements")
async def load_statements(
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """
    Load all PDF statements from the configured STATEMENTS_DIRECTORY.
    This endpoint processes all PDF files in the statements folder and 
    adds them to the vector store for RAG.
    """
    import glob
    from pathlib import Path
    
    # Get statements directory from config
    statements_dir = settings.statements_directory
    
    # Convert relative path to absolute if needed
    if not os.path.isabs(statements_dir):
        # Relative to project root (parent of backend)
        project_root = Path(__file__).parent.parent.parent
        statements_dir = str(project_root / statements_dir)
    
    if not os.path.exists(statements_dir):
        raise HTTPException(
            status_code=404, 
            detail=f"Statements directory not found: {statements_dir}"
        )
    
    # Find all PDF files
    pdf_files = glob.glob(os.path.join(statements_dir, "*.pdf"))
    
    if not pdf_files:
        return {
            "message": "No PDF files found in statements directory",
            "directory": statements_dir,
            "files_processed": 0
        }
    
    # Get or create user
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    processed_files = []
    total_transactions = 0
    errors = []
    
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        
        # Check if already processed
        existing_doc = db.query(UploadedDocument).filter(
            UploadedDocument.user_id == user.id,
            UploadedDocument.filename == filename
        ).first()
        
        if existing_doc and existing_doc.processed:
            processed_files.append({
                "filename": filename,
                "status": "skipped (already processed)",
                "transactions": existing_doc.transaction_count
            })
            continue
        
        try:
            # Create document record if not exists
            if not existing_doc:
                existing_doc = UploadedDocument(
                    user_id=user.id,
                    filename=filename,
                    file_type="pdf",
                    processed=False
                )
                db.add(existing_doc)
                db.commit()
                db.refresh(existing_doc)
            
            # Process the PDF
            extracted_transactions = await document_processor.process_pdf(pdf_path)
            
            # Save transactions
            transactions_to_add = []
            for trans_data in extracted_transactions:
                # Categorize
                category_info = categorizer.categorize(
                    trans_data.get('merchant', ''),
                    trans_data.get('description')
                )
                
                transaction = Transaction(
                    user_id=user.id,
                    transaction_date=trans_data.get('date'),
                    merchant=trans_data.get('merchant'),
                    amount=trans_data.get('amount'),
                    category=category_info.get('category'),
                    subcategory=category_info.get('subcategory'),
                    description=trans_data.get('description'),
                    source_file=filename
                )
                db.add(transaction)
                transactions_to_add.append(transaction)
            
            db.commit()
            
            # Refresh to get IDs
            for trans in transactions_to_add:
                db.refresh(trans)
            
            # Add to vector store
            transactions_dict = [
                {
                    'id': trans.id,
                    'transaction_date': trans.transaction_date,
                    'merchant': trans.merchant,
                    'amount': trans.amount,
                    'category': trans.category,
                    'subcategory': trans.subcategory,
                    'description': trans.description
                }
                for trans in transactions_to_add
            ]
            await vector_store.add_transactions_batch(transactions_dict, str(user.id))
            
            # Sync to analytics DB
            await analytics_service.sync_transactions(transactions_dict)
            
            # Update document
            existing_doc.processed = True
            existing_doc.transaction_count = len(transactions_to_add)
            db.commit()
            db.refresh(existing_doc)
            
            total_transactions += len(transactions_to_add)
            processed_files.append({
                "filename": filename,
                "status": "processed",
                "transactions": len(transactions_to_add)
            })
            
        except Exception as e:
            errors.append({
                "filename": filename,
                "error": str(e)
            })
    
    return {
        "message": f"Processed {len(processed_files)} files from {statements_dir}",
        "directory": statements_dir,
        "files_processed": len(processed_files),
        "total_transactions": total_transactions,
        "files": processed_files,
        "errors": errors if errors else None
    }


@router.get("/statements-info")
async def get_statements_info():
    """Get information about the statements directory and available files."""
    import glob
    from pathlib import Path
    
    statements_dir = settings.statements_directory
    
    # Convert relative path to absolute if needed
    if not os.path.isabs(statements_dir):
        project_root = Path(__file__).parent.parent.parent
        statements_dir = str(project_root / statements_dir)
    
    if not os.path.exists(statements_dir):
        return {
            "directory": statements_dir,
            "exists": False,
            "files": []
        }
    
    # Find all PDF files
    pdf_files = glob.glob(os.path.join(statements_dir, "*.pdf"))
    
    files_info = []
    for pdf_path in pdf_files:
        stat = os.stat(pdf_path)
        files_info.append({
            "filename": os.path.basename(pdf_path),
            "size_bytes": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    
    return {
        "directory": statements_dir,
        "exists": True,
        "file_count": len(files_info),
        "files": files_info
    }


@router.post("/reprocess-all")
async def reprocess_all_documents(
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """
    Reprocess all documents with the updated PDF parser.
    This clears existing transactions and vector store data, then re-extracts everything.
    """
    import glob
    from pathlib import Path
    
    # Get or create user
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Clear existing transactions for this user
    deleted_transactions = db.query(Transaction).filter(
        Transaction.user_id == user.id
    ).delete()
    
    # Reset all documents to unprocessed
    db.query(UploadedDocument).filter(
        UploadedDocument.user_id == user.id
    ).update({"processed": False, "transaction_count": 0})
    
    db.commit()
    
    # Clear vector store for this user
    await vector_store.delete_user_data(str(user.id))
    
    # Get statements directory
    statements_dir = settings.statements_directory
    if not os.path.isabs(statements_dir):
        project_root = Path(__file__).parent.parent.parent
        statements_dir = str(project_root / statements_dir)
    
    # Also check uploaded files directory
    upload_dir = settings.upload_directory
    if not os.path.isabs(upload_dir):
        project_root = Path(__file__).parent.parent.parent
        upload_dir = str(project_root / upload_dir)
    
    # Collect all PDF files
    pdf_files = []
    if os.path.exists(statements_dir):
        pdf_files.extend(glob.glob(os.path.join(statements_dir, "*.pdf")))
    if os.path.exists(upload_dir):
        pdf_files.extend(glob.glob(os.path.join(upload_dir, "*.pdf")))
    
    processed_files = []
    total_transactions = 0
    errors = []
    
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        
        try:
            # Get or create document record
            doc = db.query(UploadedDocument).filter(
                UploadedDocument.user_id == user.id,
                UploadedDocument.filename == filename
            ).first()
            
            if not doc:
                doc = UploadedDocument(
                    user_id=user.id,
                    filename=filename,
                    file_type="pdf",
                    processed=False
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
            
            # Process the PDF with updated parser
            extracted_transactions = await document_processor.process_pdf(pdf_path)
            
            # Save transactions
            transactions_to_add = []
            for trans_data in extracted_transactions:
                category_info = categorizer.categorize(
                    trans_data.get('merchant', ''),
                    trans_data.get('description')
                )
                
                transaction = Transaction(
                    user_id=user.id,
                    transaction_date=trans_data.get('date'),
                    merchant=trans_data.get('merchant'),
                    amount=trans_data.get('amount'),
                    category=category_info.get('category'),
                    subcategory=category_info.get('subcategory'),
                    description=trans_data.get('description'),
                    source_file=filename
                )
                db.add(transaction)
                transactions_to_add.append(transaction)
            
            db.commit()
            
            # Refresh to get IDs
            for trans in transactions_to_add:
                db.refresh(trans)
            
            # Add to vector store
            transactions_dict = [
                {
                    'id': str(trans.id),
                    'transaction_date': trans.transaction_date,
                    'merchant': trans.merchant,
                    'amount': float(trans.amount) if trans.amount else 0,
                    'category': trans.category,
                    'subcategory': trans.subcategory,
                    'description': trans.description
                }
                for trans in transactions_to_add
            ]
            await vector_store.add_transactions_batch(transactions_dict, str(user.id))
            
            # Sync to analytics DB
            await analytics_service.sync_transactions(transactions_dict)
            
            # Update document
            doc.processed = True
            doc.transaction_count = len(transactions_to_add)
            db.commit()
            
            total_transactions += len(transactions_to_add)
            processed_files.append({
                "filename": filename,
                "status": "reprocessed",
                "transactions": len(transactions_to_add)
            })
            
        except Exception as e:
            errors.append({
                "filename": filename,
                "error": str(e)
            })
    
    # Generate category summaries for better RAG answers on aggregate questions
    try:
        all_transactions = db.query(Transaction).filter(
            Transaction.user_id == user.id
        ).all()
        all_trans_dict = [
            {
                'id': str(t.id),
                'transaction_date': t.transaction_date,
                'merchant': t.merchant,
                'amount': float(t.amount) if t.amount else 0,
                'category': t.category,
                'subcategory': t.subcategory
            }
            for t in all_transactions
        ]
        summaries_added = await vector_store.add_category_summaries(all_trans_dict, str(user.id))
    except Exception as e:
        print(f"Error generating category summaries: {e}")
        summaries_added = 0
    
    return {
        "message": f"Reprocessed {len(processed_files)} files",
        "deleted_transactions": deleted_transactions,
        "files_processed": len(processed_files),
        "total_transactions": total_transactions,
        "files": processed_files,
        "errors": errors if errors else None,
        "category_summaries_added": summaries_added
    }


@router.post("/categorize-uncategorized")
async def categorize_uncategorized_transactions(
    user_email: str = "default@example.com",
    db: Session = Depends(get_db)
):
    """
    Use LLM to categorize all transactions currently marked as 'Uncategorized'.
    This batches unique merchant names and sends them to the LLM in a single call
    for efficient categorization.
    """
    # Get user
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all uncategorized transactions
    uncategorized_transactions = db.query(Transaction).filter(
        Transaction.user_id == user.id,
        Transaction.category == "Uncategorized"
    ).all()
    
    if not uncategorized_transactions:
        return {
            "message": "No uncategorized transactions found",
            "transactions_updated": 0,
            "merchants_categorized": 0
        }
    
    # Get unique merchant names
    unique_merchants = list(set(
        t.merchant for t in uncategorized_transactions 
        if t.merchant
    ))
    
    # Batch categorize with LLM
    merchant_categories = categorizer.batch_categorize_merchants(unique_merchants)
    
    # Update transactions in database
    updated_count = 0
    category_updates = {}  # Track what categories were assigned
    
    for transaction in uncategorized_transactions:
        if transaction.merchant and transaction.merchant in merchant_categories:
            new_category = merchant_categories[transaction.merchant]
            if new_category != "Uncategorized":
                transaction.category = new_category
                updated_count += 1
                
                if new_category not in category_updates:
                    category_updates[new_category] = []
                category_updates[new_category].append(transaction.merchant)
    
    db.commit()
    
    # Sync to analytics DB and regenerate vector summaries
    all_transactions = db.query(Transaction).filter(
        Transaction.user_id == user.id
    ).all()
    
    all_trans_dict = [
        {
            'id': str(t.id),
            'transaction_date': t.transaction_date,
            'merchant': t.merchant,
            'amount': float(t.amount) if t.amount else 0,
            'category': t.category,
            'subcategory': t.subcategory,
            'description': t.description
        }
        for t in all_transactions
    ]
    
    # Sync to analytics
    await analytics_service.sync_transactions(all_trans_dict)
    
    # Regenerate category summaries in vector store
    summaries_added = await vector_store.add_category_summaries(all_trans_dict, str(user.id))
    
    # Create summary of categorizations
    categorization_summary = {
        cat: list(set(merchants))[:5]  # Show up to 5 unique merchants per category
        for cat, merchants in category_updates.items()
    }
    
    return {
        "message": f"Categorized {updated_count} transactions",
        "transactions_updated": updated_count,
        "merchants_processed": len(unique_merchants),
        "categories_assigned": categorization_summary,
        "category_summaries_regenerated": summaries_added
    }

