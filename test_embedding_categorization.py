"""
Test script to evaluate embedding-based categorization accuracy.
Compares current local embeddings (sentence-transformers) for transaction categorization.
"""

import sys
sys.path.insert(0, '/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/PersonalFinancePlanning_RAG/backend')

from sentence_transformers import SentenceTransformer
import numpy as np

# Load the model (same one used in the app)
print("Loading embedding model...")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Categories with descriptions for better embedding matching
CATEGORIES = {
    "Food & Dining": "restaurant cafe coffee pizza burger food dining bar grill kitchen eating out meals",
    "Groceries": "grocery store supermarket whole foods trader joe walmart target costco food shopping produce",
    "Transportation": "uber lyft taxi gas fuel shell chevron exxon parking toll transit ride car driving",
    "Shopping": "amazon retail store mall purchase buy merchandise goods clothing electronics",
    "Entertainment": "netflix spotify movie theater cinema concert game streaming music video",
    "Utilities": "electric gas water internet cable phone utility power energy bill payment service provider",
    "Healthcare": "pharmacy cvs walgreens hospital clinic doctor medical health dental vision pet grooming",
    "Travel": "airline hotel airbnb flight booking vacation trip",
    "Subscriptions": "subscription monthly membership software service cloud platform hosting SaaS",
}

# Sample uncategorized merchants from your data
UNCATEGORIZED_MERCHANTS = [
    "CURSOR USAGE FEB NEW YORK",
    "GOOGLE *CLOUD NMxVBL",
    "NTTA ONLINE",
    "FIGO PET INS CHICAGO",
    "OPENAI SAN FRANCISCO",
    "THE HOME DEPOT #6572 FLOWER MOUND",
    "MERITAGE HOMES OF TEXA AUSTIN",
    "TX.GOV*SERVICEFEE-DIR",
    "GROOMING PLACE FLOWER MOUND",
    "PLAYGROUND AI SAN FRANCISCO",
    "UT RECEIVABLES-WEB AUSTIN",
    "DENTON VEHREG",
    "ARCH BROWS THREADING & COLLEYVILLE",
    "WEB*NETWORKSOLUTIONS",
    "5776 GREAT CLIPS AT MA FLOWER MOUND",
]

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def test_categorization():
    print(f"\nCreating embeddings for {len(CATEGORIES)} categories...")
    
    # Create category embeddings
    category_texts = list(CATEGORIES.values())
    category_names = list(CATEGORIES.keys())
    category_embeddings = model.encode(category_texts)
    
    print(f"Testing {len(UNCATEGORIZED_MERCHANTS)} merchants...\n")
    print("=" * 80)
    print(f"{'Merchant':<40} {'Best Match':<20} {'Score':<10}")
    print("=" * 80)
    
    results = []
    for merchant in UNCATEGORIZED_MERCHANTS:
        # Create merchant embedding
        merchant_embedding = model.encode(merchant)
        
        # Find best matching category
        similarities = [cosine_similarity(merchant_embedding, cat_emb) for cat_emb in category_embeddings]
        best_idx = np.argmax(similarities)
        best_score = similarities[best_idx]
        best_category = category_names[best_idx]
        
        # Show top 2 matches for comparison
        sorted_indices = np.argsort(similarities)[::-1]
        top2 = [(category_names[i], similarities[i]) for i in sorted_indices[:2]]
        
        status = "✓" if best_score > 0.35 else "?"  # Threshold for confidence
        
        print(f"{merchant:<40} {best_category:<20} {best_score:.3f} {status}")
        results.append({
            'merchant': merchant,
            'category': best_category,
            'score': best_score,
            'confident': best_score > 0.35
        })
    
    print("=" * 80)
    
    # Summary
    confident = sum(1 for r in results if r['confident'])
    print(f"\nSummary:")
    print(f"  Total merchants: {len(results)}")
    print(f"  High confidence (>0.35): {confident} ({confident/len(results)*100:.0f}%)")
    print(f"  Low confidence (<0.35): {len(results) - confident} ({(len(results)-confident)/len(results)*100:.0f}%)")
    
    print("\n🔍 Analysis:")
    print("  - Scores > 0.4: Very confident, likely correct")
    print("  - Scores 0.3-0.4: Moderate confidence")
    print("  - Scores < 0.3: Low confidence, may need LLM fallback")

if __name__ == "__main__":
    test_categorization()
