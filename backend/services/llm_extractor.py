"""
LLM-based PDF transaction extractor using Gemini Vision.
Extracts transactions from credit card statement images using AI.
"""

import json
import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from pdf2image import convert_from_path
import google.generativeai as genai

from config import settings
from .metrics import metrics_collector, Timer, MetricsCollector


class LLMExtractor:
    """Service for extracting transactions from PDFs using LLM vision."""
    
    def __init__(self):
        """Initialize the LLM extractor."""
        self._model = None
    
    @property
    def model(self):
        """Get or create Gemini model for vision."""
        if self._model is None and settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
            self._model = genai.GenerativeModel('gemini-2.0-flash')
        return self._model
    
    async def extract_transactions(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract transactions from a PDF using Gemini Vision.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of extracted transactions
        """
        if not self.model:
            raise ValueError("Gemini API key not configured")
        
        transactions = []
        filename = os.path.basename(file_path)
        
        with Timer(
            MetricsCollector.FLOW_DOCUMENT,
            "llm_extract_pdf",
            metadata={"file": filename}
        ):
            try:
                # Convert PDF pages to images
                images = convert_from_path(file_path, dpi=150)
                
                for page_num, image in enumerate(images):
                    page_transactions = await self._extract_from_image(image, page_num + 1)
                    transactions.extend(page_transactions)
                
            except Exception as e:
                print(f"LLM extraction failed: {e}")
                metrics_collector.record_error(
                    MetricsCollector.FLOW_DOCUMENT,
                    "llm_extraction_error"
                )
                raise
        
        # Record metrics
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_DOCUMENT,
            "extraction_method_llm"
        )
        metrics_collector.increment_counter(
            MetricsCollector.FLOW_DOCUMENT,
            "transactions_extracted",
            len(transactions)
        )
        
        return self._deduplicate_transactions(transactions)
    
    async def _extract_from_image(self, image, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract transactions from a single page image.
        
        Args:
            image: PIL Image of the PDF page
            page_num: Page number for logging
            
        Returns:
            List of transactions from this page
        """
        prompt = """Analyze this credit card statement page and extract ALL transactions.

For each transaction, identify:
- date: The transaction date (format as YYYY-MM-DD)
- merchant: The merchant/store name (clean it up, remove location codes)
- amount: The transaction amount as a positive number (exclude credits/payments)

IMPORTANT:
- Only extract actual purchase transactions (positive amounts)
- Skip payments, credits, refunds, and fees
- Skip header/footer information
- Skip summary lines (Previous Balance, New Balance, etc.)

Return ONLY a valid JSON array with no additional text or explanation.
If no transactions found on this page, return an empty array: []

Example output format:
[
  {"date": "2024-12-15", "merchant": "AMAZON.COM", "amount": 45.99},
  {"date": "2024-12-16", "merchant": "STARBUCKS", "amount": 7.50}
]"""

        try:
            response = self.model.generate_content([image, prompt])
            response_text = response.text.strip()
            
            # Clean up response - remove markdown code blocks if present
            if response_text.startswith("```"):
                # Remove ```json and ``` markers
                response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
                response_text = re.sub(r'\s*```$', '', response_text)
            
            # Parse JSON response
            transactions_data = json.loads(response_text)
            
            if not isinstance(transactions_data, list):
                return []
            
            # Convert to standard format
            transactions = []
            for trans in transactions_data:
                try:
                    date_str = trans.get('date', '')
                    date_obj = self._parse_date(date_str)
                    
                    if date_obj and trans.get('amount'):
                        transactions.append({
                            'date': date_obj,
                            'merchant': self._clean_merchant(trans.get('merchant', '')),
                            'amount': abs(float(trans.get('amount', 0))),
                            'raw_text': f"LLM extracted from page {page_num}"
                        })
                except (ValueError, TypeError) as e:
                    print(f"Error parsing transaction: {e}")
                    continue
            
            return transactions
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error on page {page_num}: {e}")
            print(f"Response was: {response_text[:200]}...")
            return []
        except Exception as e:
            print(f"Error extracting from page {page_num}: {e}")
            return []
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
        
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y', '%m/%d/%y',
            '%d/%m/%Y', '%d/%m/%y',
            '%m-%d-%Y', '%m-%d-%y',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def _clean_merchant(self, merchant: str) -> str:
        """Clean up merchant name."""
        if not merchant:
            return ""
        
        # Remove trailing state abbreviations
        merchant = re.sub(r'\s+[A-Z]{2}$', '', merchant.strip())
        # Remove extra whitespace
        merchant = ' '.join(merchant.split())
        return merchant.strip()
    
    def _deduplicate_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate transactions."""
        seen = set()
        unique = []
        
        for trans in transactions:
            key = (
                trans.get('date'),
                trans.get('merchant', '').lower(),
                trans.get('amount')
            )
            
            if key not in seen:
                seen.add(key)
                unique.append(trans)
        
        return unique


# Global instance
llm_extractor = LLMExtractor()
