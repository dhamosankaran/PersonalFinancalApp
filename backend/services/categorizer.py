"""
Categorization service for transactions.
Uses rule-based matching and optional LLM refinement.
"""

from typing import Optional, Dict, List
import re

from config import settings
from .llm_factory import llm_factory


class Categorizer:
    """Service for categorizing transactions."""
    
    # Rule-based category mappings
    CATEGORY_RULES = {
        "Food & Dining": {
            "keywords": [
                "restaurant", "cafe", "coffee", "pizza", "burger", "sushi",
                "food", "dining", "bar", "pub", "grill", "kitchen",
                "doordash", "ubereats", "grubhub", "postmates"
            ],
            "merchants": [
                "mcdonalds", "starbucks", "chipotle", "subway", "dominos",
                "panera", "chick-fil-a", "wendys", "taco bell"
            ]
        },
        "Groceries": {
            "keywords": [
                "market", "grocery", "supermarket", "whole foods", "trader joe",
                "safeway", "kroger", "walmart", "target", "costco", "sams club"
            ],
            "merchants": [
                "whole foods", "trader joes", "safeway", "kroger", "publix",
                "aldi", "lidl", "sprouts"
            ]
        },
        "Transportation": {
            "keywords": [
                "uber", "lyft", "taxi", "gas", "fuel", "shell", "chevron",
                "exxon", "bp", "parking", "toll", "transit"
            ],
            "merchants": [
                "uber", "lyft", "shell", "chevron", "exxon", "mobil"
            ]
        },
        "Shopping": {
            "keywords": [
                "amazon", "ebay", "walmart", "target", "bestbuy", "apple",
                "store", "shop", "retail", "mall"
            ],
            "merchants": [
                "amazon", "ebay", "walmart", "target", "bestbuy", "apple store"
            ]
        },
        "Entertainment": {
            "keywords": [
                "netflix", "spotify", "hulu", "disney", "hbo", "amazon prime",
                "movie", "theater", "cinema", "concert", "ticket", "game"
            ],
            "merchants": [
                "netflix", "spotify", "hulu", "disney plus", "youtube premium"
            ]
        },
        "Utilities": {
            "keywords": [
                "electric", "gas", "water", "internet", "cable", "phone",
                "utility", "power", "energy", "verizon", "at&t", "comcast"
            ],
            "merchants": [
                "verizon", "at&t", "tmobile", "comcast", "spectrum"
            ]
        },
        "Healthcare": {
            "keywords": [
                "pharmacy", "cvs", "walgreens", "hospital", "clinic", "doctor",
                "medical", "health", "dental", "vision"
            ],
            "merchants": [
                "cvs", "walgreens", "rite aid"
            ]
        },
        "Travel": {
            "keywords": [
                "airline", "hotel", "airbnb", "rental car", "flight", "booking",
                "expedia", "priceline", "southwest", "delta", "united", "american airlines"
            ],
            "merchants": [
                "airbnb", "booking.com", "expedia", "southwest", "delta", "united"
            ]
        },
        "Subscriptions": {
            "keywords": [
                "subscription", "monthly", "membership", "annual fee"
            ],
            "merchants": [
                "netflix", "spotify", "adobe", "microsoft", "apple icloud"
            ]
        },
    }
    
    def __init__(self):
        """Initialize the categorizer."""
        # LLM client is now obtained from factory
        pass
    
    @property
    def client(self):
        """Get raw LLM client from factory."""
        return llm_factory.get_raw_client()
    
    def categorize(self, merchant: str, description: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        Categorize a transaction based on merchant and description.
        
        Args:
            merchant: Merchant name
            description: Optional transaction description
            
        Returns:
            Dictionary with 'category' and 'subcategory'
        """
        # First, try rule-based categorization
        category = self._rule_based_categorization(merchant, description)
        
        if category:
            return {"category": category, "subcategory": None}
        
        # If no match and LLM is available, use LLM refinement
        if self.client:
            return self._llm_categorization(merchant, description)
        
        return {"category": "Uncategorized", "subcategory": None}
    
    def _rule_based_categorization(self, merchant: str, description: Optional[str] = None) -> Optional[str]:
        """Rule-based categorization using keywords and merchant patterns."""
        if not merchant:
            return None
        
        merchant_lower = merchant.lower()
        desc_lower = description.lower() if description else ""
        combined_text = f"{merchant_lower} {desc_lower}"
        
        # Check each category
        for category, rules in self.CATEGORY_RULES.items():
            # Check merchant names
            for merchant_pattern in rules.get("merchants", []):
                if merchant_pattern in merchant_lower:
                    return category
            
            # Check keywords
            for keyword in rules.get("keywords", []):
                if keyword in combined_text:
                    return category
        
        return None
    
    def _llm_categorization(self, merchant: str, description: Optional[str] = None) -> Dict[str, Optional[str]]:
        """LLM-based categorization for ambiguous cases."""
        try:
            categories_list = list(self.CATEGORY_RULES.keys())
            
            prompt = f"""Categorize this transaction into one of the following categories:
{', '.join(categories_list)}

Transaction Details:
Merchant: {merchant}
Description: {description or 'N/A'}

Respond with ONLY the category name, nothing else. If uncertain, respond with "Uncategorized"."""
            
            category = self._call_llm(
                system_prompt="You are a financial transaction categorization expert.",
                user_prompt=prompt,
                max_tokens=20
            )
            
            if category:
                category = category.strip()
                # Validate the response
                if category in categories_list:
                    return {"category": category, "subcategory": None}
            
        except Exception as e:
            print(f"LLM categorization failed: {e}")
        
        return {"category": "Uncategorized", "subcategory": None}
    
    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 100) -> Optional[str]:
        """
        Call the LLM (OpenAI or Gemini) based on current provider.
        
        Args:
            system_prompt: System message for the LLM
            user_prompt: User message/question
            max_tokens: Maximum tokens in response
            
        Returns:
            Response text or None if failed
        """
        client = self.client
        if not client:
            return None
        
        provider = llm_factory.get_current_provider()
        
        try:
            if provider == "openai" or hasattr(client, 'chat'):
                # OpenAI client
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
            else:
                # Gemini client (GenerativeModel)
                combined_prompt = f"{system_prompt}\n\n{user_prompt}"
                response = client.generate_content(
                    combined_prompt,
                    generation_config={
                        "temperature": 0,
                        "max_output_tokens": max_tokens
                    }
                )
                return response.text
        except Exception as e:
            print(f"LLM call failed: {e}")
            return None
    
    def batch_categorize_merchants(self, merchants: List[str]) -> Dict[str, str]:
        """
        Batch categorize multiple merchants in a single LLM call.
        Much more efficient than categorizing one at a time.
        
        Args:
            merchants: List of unique merchant names to categorize
            
        Returns:
            Dictionary mapping merchant name to category
        """
        if not merchants or not self.client:
            return {}
        
        # First, filter out merchants that can be rule-based categorized
        uncategorized_merchants = []
        result = {}
        
        for merchant in merchants:
            category = self._rule_based_categorization(merchant)
            if category:
                result[merchant] = category
            else:
                uncategorized_merchants.append(merchant)
        
        if not uncategorized_merchants:
            return result
        
        # Batch categorize remaining merchants with LLM
        categories_list = list(self.CATEGORY_RULES.keys())
        
        # Create a numbered list of merchants for the prompt
        merchant_list = "\n".join([f"{i+1}. {m}" for i, m in enumerate(uncategorized_merchants)])
        
        prompt = f"""Categorize each of the following merchants into one of these categories:
{', '.join(categories_list)}

Merchants to categorize:
{merchant_list}

Respond with ONLY a JSON object mapping each merchant name exactly as provided to its category.
Example format: {{"MERCHANT NAME": "Category", "ANOTHER MERCHANT": "Category"}}

If a merchant is unclear, use "Uncategorized". Only use the exact category names provided."""

        try:
            response_text = self._call_llm(
                system_prompt="You are a financial transaction categorization expert. Respond only with valid JSON.",
                user_prompt=prompt,
                max_tokens=2000
            )
            
            if not response_text:
                raise Exception("No response from LLM")
            
            response_text = response_text.strip()
            
            # Parse JSON response
            import json
            # Handle potential markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            
            llm_categories = json.loads(response_text)
            
            # Validate and merge results
            for merchant, category in llm_categories.items():
                if category in categories_list or category == "Uncategorized":
                    result[merchant] = category
                else:
                    result[merchant] = "Uncategorized"
            
            # Add any merchants that weren't in the response
            for merchant in uncategorized_merchants:
                if merchant not in result:
                    result[merchant] = "Uncategorized"
                    
        except Exception as e:
            print(f"Batch LLM categorization failed: {e}")
            # Fall back to Uncategorized for all
            for merchant in uncategorized_merchants:
                result[merchant] = "Uncategorized"
        
        return result

    
    def detect_recurring(self, transactions: List[Dict]) -> List[str]:
        """
        Detect recurring transactions based on patterns.
        
        Args:
            transactions: List of transactions with same merchant
            
        Returns:
            List of transaction IDs that are recurring
        """
        # Simple heuristic: if same merchant + similar amount appears monthly
        # This is a placeholder - can be enhanced with more sophisticated logic
        recurring_ids = []
        
        if len(transactions) >= 3:
            # Group by month
            monthly_groups = {}
            for trans in transactions:
                month = trans.get('transaction_date', '').rsplit('-', 1)[0] if trans.get('transaction_date') else None
                if month:
                    if month not in monthly_groups:
                        monthly_groups[month] = []
                    monthly_groups[month].append(trans)
            
            # If appears in 3+ consecutive months with similar amounts
            if len(monthly_groups) >= 3:
                amounts = [t.get('amount') for t in transactions if t.get('amount')]
                if amounts:
                    avg_amount = sum(amounts) / len(amounts)
                    # If amount variance is low (< 10%), likely recurring
                    variance = max(amounts) - min(amounts)
                    if variance / avg_amount < 0.1:
                        recurring_ids = [str(t.get('id')) for t in transactions if t.get('id')]
        
        return recurring_ids
