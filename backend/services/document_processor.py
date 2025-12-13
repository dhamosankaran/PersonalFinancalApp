"""
PDF and CSV document processing service.
Extracts transactions from credit card statements and bank exports.
Instrumented with metrics collection for observability.
"""

import pdfplumber
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import pandas as pd
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import io
import os
import time

from config import settings
from .metrics import metrics_collector, Timer, MetricsCollector


class DocumentProcessor:
    """Service for processing PDF and CSV documents."""
    
    def __init__(self):
        """Initialize the document processor."""
        self.tesseract_path = settings.tesseract_path
        if os.path.exists(self.tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
    
    async def process_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Process a PDF file and extract transactions.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of extracted transactions
        """
        extraction_method = "unknown"
        
        with Timer(
            MetricsCollector.FLOW_DOCUMENT,
            "process_pdf",
            metadata={"file": os.path.basename(file_path)}
        ):
            # Try PDFPlumber first (best for digital PDFs)
            transactions = await self._extract_with_pdfplumber(file_path)
            extraction_method = "pdfplumber"
            
            if not transactions or len(transactions) < 3:
                # Fallback to PyMuPDF
                transactions = await self._extract_with_pymupdf(file_path)
                extraction_method = "pymupdf"
            
            if not transactions or len(transactions) < 3:
                # Last resort: OCR
                transactions = await self._extract_with_ocr(file_path)
                extraction_method = "ocr"
        
        # Record metrics
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_DOCUMENT,
            "documents_processed"
        )
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_DOCUMENT,
            f"extraction_method_{extraction_method}"
        )
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_DOCUMENT,
            "transactions_extracted",
            len(transactions)
        )
        metrics_collector.add_histogram(
            MetricsCollector.FLOW_DOCUMENT,
            "transactions_per_document",
            len(transactions)
        )
        
        return transactions
    
    async def _extract_with_pdfplumber(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract transactions using PDFPlumber."""
        transactions = []
        filename = os.path.basename(file_path)
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # Extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        transactions.extend(self._parse_table(table, filename))
                    
                    # Also extract text for non-tabular data
                    text = page.extract_text()
                    if text:
                        transactions.extend(self._parse_text(text, filename))
        except Exception as e:
            print(f"PDFPlumber extraction failed: {e}")
        
        return self._deduplicate_transactions(transactions)
    
    async def _extract_with_pymupdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract transactions using PyMuPDF."""
        transactions = []
        filename = os.path.basename(file_path)
        
        try:
            doc = fitz.open(file_path)
            for page in doc:
                text = page.get_text()
                transactions.extend(self._parse_text(text, filename))
        except Exception as e:
            print(f"PyMuPDF extraction failed: {e}")
        
        return self._deduplicate_transactions(transactions)
    
    async def _extract_with_ocr(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract transactions using OCR (for image-only PDFs)."""
        transactions = []
        filename = os.path.basename(file_path)
        
        try:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                # Convert page to image
                page = doc[page_num]
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Perform OCR
                text = pytesseract.image_to_string(img)
                transactions.extend(self._parse_text(text, filename))
        except Exception as e:
            print(f"OCR extraction failed: {e}")
        
        return self._deduplicate_transactions(transactions)
    
    async def process_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Process a CSV file and extract transactions.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            List of extracted transactions
        """
        transactions = []
        
        try:
            # Try to detect CSV dialect
            df = pd.read_csv(file_path, encoding='utf-8')
            
            # Normalize column names
            df.columns = df.columns.str.lower().str.strip()
            
            # Map common column names
            column_mapping = {
                'date': ['date', 'transaction date', 'post date', 'trans date'],
                'merchant': ['merchant', 'description', 'desc', 'payee', 'vendor'],
                'amount': ['amount', 'debit', 'credit', 'transaction amount'],
            }
            
            # Find actual column names
            actual_cols = {}
            for key, possible_names in column_mapping.items():
                for col in df.columns:
                    if any(name in col for name in possible_names):
                        actual_cols[key] = col
                        break
            
            # Extract transactions
            for _, row in df.iterrows():
                transaction = {}
                
                if 'date' in actual_cols:
                    transaction['date'] = self._parse_date(str(row[actual_cols['date']]))
                
                if 'merchant' in actual_cols:
                    transaction['merchant'] = str(row[actual_cols['merchant']]).strip()
                
                if 'amount' in actual_cols:
                    transaction['amount'] = self._parse_amount(str(row[actual_cols['amount']]))
                
                if transaction.get('date') and transaction.get('amount'):
                    transactions.append(transaction)
        
        except Exception as e:
            print(f"CSV processing failed: {e}")
        
        return transactions
    
    def _parse_table(self, table: List[List[str]], source_filename: str = None) -> List[Dict[str, Any]]:
        """Parse a table extracted from PDF."""
        transactions = []
        inferred_year = self._infer_year_from_filename(source_filename)
        
        for row in table:
            if not row or len(row) < 3:
                continue
            
            # Try to find date, merchant, and amount in the row
            transaction = {}
            
            for cell in row:
                if not cell:
                    continue
                
                # Try to parse as date
                parsed_date = self._parse_date_with_year(cell, inferred_year) or self._parse_date(cell)
                if parsed_date and not transaction.get('date'):
                    transaction['date'] = parsed_date
                
                # Try to parse as amount
                parsed_amount = self._parse_amount(cell)
                if parsed_amount is not None and not transaction.get('amount'):
                    transaction['amount'] = parsed_amount
                
                # Assume remaining text is merchant name
                if not transaction.get('merchant') and not parsed_date and parsed_amount is None:
                    if len(cell.strip()) > 3:
                        transaction['merchant'] = self._clean_merchant_name(cell.strip())
            
            if transaction.get('date') and transaction.get('amount'):
                # Skip header/summary lines that got picked up
                merchant = transaction.get('merchant', '').lower()
                skip_patterns = ['payment due', 'due date', 'minimum payment', 'previous balance', 
                                'new balance', 'credit limit', 'billing period']
                if not any(skip in merchant for skip in skip_patterns):
                    transactions.append(transaction)
        
        return transactions
    
    def _parse_text(self, text: str, source_filename: str = None) -> List[Dict[str, Any]]:
        """
        Parse unstructured text for transactions.
        Supports multiple credit card statement formats.
        
        Args:
            text: Raw text from PDF
            source_filename: Original filename for year inference
        """
        transactions = []
        lines = text.split('\n')
        
        # Extract year from PDF content (e.g., "New balance as of 12/20/25" -> 2025)
        # This is more reliable than inferring from filename
        inferred_year = self._extract_year_from_text(text)
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip header/summary lines - only skip if line STARTS with these phrases
            # (not just contains them, since trailing footer text can appear after transactions)
            skip_starters = [
                'previous balance', 'new balance', 'payment due', 'minimum payment',
                'total fees', 'total interest', 'billing period', 'account summary',
                'credit limit', 'available credit', 'account number', 'opening/closing'
            ]
            line_lower = line.lower()
            if any(line_lower.startswith(skip) for skip in skip_starters):
                continue
            # Also skip page headers
            if line_lower.startswith('page ') or line_lower == 'page':
                continue
            
            transaction = self._extract_transaction_from_line(line, inferred_year)
            if transaction:
                transactions.append(transaction)
        
        return transactions
    
    def _extract_transaction_from_line(self, line: str, inferred_year: int = None) -> Optional[Dict[str, Any]]:
        """
        Extract transaction from a single line using multiple patterns.
        
        Supported formats:
        - Citi: "12/20 CHIPOTLE ONLINE CHIPOTLE.COM CA $7.17"
        - Citi with duplicate date: "01/08 01/08 STARBUCKS 800-782-7282 WA $10.00"
        - Citi payment: "09/28 ONLINE PAYMENT, THANK YOU -$1,562.16"
        - Standard: "12/01/2023 AMAZON.COM $45.99"
        """
        # Pattern 1: Citi format - MM/DD at start, optional -$amount anywhere in line
        # Handles: "12/20 MERCHANT NAME CITY STATE $XX.XX" or "-$XX.XX"
        citi_pattern = r'^(\d{1,2}/\d{1,2})(?:\s+\d{1,2}/\d{1,2})?\s+(.+?)\s+(-?)\$(\d[\d,]*\.\d{2})'
        match = re.match(citi_pattern, line)
        if match:
            date_str, merchant, is_negative, amount_str = match.groups()
            
            # Skip payment transactions (negative amounts are usually payments/credits)
            if is_negative == '-':
                return None
            
            # Skip only credit card payments (not bill payments like TXU, ATT)
            # Also skip header lines that may accidentally match (like "Payment due date:")
            merchant_lower = merchant.lower()
            skip_patterns = ['online payment', 'thank you', 'autopay', 'due date', 'minimum payment', 'payment due']
            if any(skip in merchant_lower for skip in skip_patterns):
                return None
            
            # Clean up merchant - remove trailing state abbreviation
            merchant = self._clean_merchant_name(merchant)
            date_obj = self._parse_date_with_year(date_str, inferred_year)
            amount = self._parse_amount(amount_str)
            if date_obj and amount is not None and merchant:
                return {
                    'date': date_obj,
                    'merchant': merchant,
                    'amount': amount,
                    'raw_text': line
                }
        
        # Pattern 2: Standard format with full date
        # Handles: "12/01/2023 AMAZON.COM $45.99" or "12-01-2023 AMAZON.COM 45.99"
        standard_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(.+?)\s+[\$€£]?([\d,]+\.\d{2})'
        match = re.search(standard_pattern, line)
        if match:
            date_str, merchant, amount_str = match.groups()
            merchant = self._clean_merchant_name(merchant)
            date_obj = self._parse_date(date_str)
            amount = self._parse_amount(amount_str)
            if date_obj and amount is not None and merchant:
                return {
                    'date': date_obj,
                    'merchant': merchant,
                    'amount': amount,
                    'raw_text': line
                }
        
        return None
    
    def _clean_merchant_name(self, merchant: str) -> str:
        """Clean up merchant name by removing location codes and extra whitespace."""
        # Remove trailing 2-letter state abbreviation
        merchant = re.sub(r'\s+[A-Z]{2}$', '', merchant.strip())
        # Remove trailing phone numbers
        merchant = re.sub(r'\s+\d{3}[-.]?\d{3}[-.]?\d{4}\s*$', '', merchant)
        # Remove extra whitespace
        merchant = ' '.join(merchant.split())
        return merchant.strip()
    
    def _infer_year_from_filename(self, filename: str) -> int:
        """
        Fallback year inference. Returns current year.
        Primary year extraction should use _extract_year_from_text instead.
        
        Args:
            filename: Original filename (not used - kept for API compatibility)
            
        Returns:
            Current year as default
        """
        return datetime.now().year
    
    def _extract_year_from_text(self, text: str) -> int:
        """
        Extract year from PDF text content by looking for date patterns.
        
        Args:
            text: PDF text content
            
        Returns:
            Extracted year or 2025 as default
        """
        if not text:
            return 2025
        
        # Look for dates like "10/20/25" or "New balance as of 10/20/25"
        # Format: MM/DD/YY
        match = re.search(r'\d{1,2}/\d{1,2}/(\d{2})\b', text)
        if match:
            year_suffix = int(match.group(1))
            # 00-50 -> 2000-2050, 51-99 -> 1951-1999
            if year_suffix <= 50:
                return 2000 + year_suffix
            else:
                return 1900 + year_suffix
        
        # Look for full year like "2025"
        match = re.search(r'(20\d{2})', text)
        if match:
            return int(match.group(1))
        
        return 2025
    
    def _parse_date_with_year(self, date_str: str, year: int = None) -> Optional[datetime]:
        """
        Parse a MM/DD date string and add the inferred year.
        
        Args:
            date_str: Date string like "12/20" or "01/08"
            year: Year to use (e.g., 2020)
            
        Returns:
            datetime object or None
        """
        if not date_str:
            return None
        
        if year is None:
            year = datetime.now().year
        
        try:
            # Parse MM/DD
            parts = date_str.strip().split('/')
            if len(parts) == 2:
                month, day = int(parts[0]), int(parts[1])
                return datetime(year, month, day)
        except (ValueError, IndexError):
            pass
        
        # Fall back to standard parsing
        return self._parse_date(date_str)
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats.""" 
        if not date_str:
            return None
        
        date_formats = [
            '%m/%d/%Y', '%m/%d/%y',
            '%d/%m/%Y', '%d/%m/%y',
            '%Y-%m-%d', '%m-%d-%Y',
            '%b %d, %Y', '%B %d, %Y',
            '%d %b %Y', '%d %B %Y',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        
        return None
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount from string."""
        if not amount_str:
            return None
        
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[^\d,.-]', '', amount_str)
        cleaned = cleaned.replace(',', '')
        
        try:
            amount = float(cleaned)
            return abs(amount)  # Always return positive amount
        except:
            return None
    
    def _deduplicate_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate transactions."""
        seen = set()
        unique_transactions = []
        
        for trans in transactions:
            # Create a unique key
            key = (
                trans.get('date'),
                trans.get('merchant', '').lower(),
                trans.get('amount')
            )
            
            if key not in seen:
                seen.add(key)
                unique_transactions.append(trans)
        
        return unique_transactions
