"""
Test script to compare embedding models for transaction categorization:
1. Local: sentence-transformers/all-MiniLM-L6-v2
2. OpenAI: text-embedding-3-small
3. Gemini: text-embedding-004

Run from project root: python test_embedding_comparison.py
"""

import os
import sys
sys.path.insert(0, '/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/PersonalFinancePlanning_RAG/backend')

from dotenv import load_dotenv
import numpy as np

# Load environment variables
load_dotenv('/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/PersonalFinancePlanning_RAG/.env')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')

# Categories with descriptions
CATEGORIES = {
    "Food & Dining": "restaurant cafe coffee pizza burger food dining bar grill kitchen eating out meals",
    "Groceries": "grocery store supermarket whole foods trader joe walmart target costco food shopping produce",
    "Transportation": "uber lyft taxi gas fuel shell chevron exxon parking toll transit ride car driving",
    "Shopping": "amazon retail store mall purchase buy merchandise goods clothing electronics home depot hardware",
    "Entertainment": "netflix spotify movie theater cinema concert game streaming music video",
    "Utilities": "electric gas water internet cable phone utility power energy bill payment service provider",
    "Healthcare": "pharmacy cvs walgreens hospital clinic doctor medical health dental vision pet insurance grooming salon haircut",
    "Travel": "airline hotel airbnb flight booking vacation trip",
    "Subscriptions": "subscription monthly membership software service cloud platform hosting SaaS AI cursor openai google cloud",
}

# Sample uncategorized merchants
MERCHANTS = [
    ("CURSOR USAGE FEB NEW YORK", "Subscriptions"),  # Expected category
    ("GOOGLE *CLOUD NMxVBL", "Subscriptions"),
    ("NTTA ONLINE", "Transportation"),
    ("FIGO PET INS CHICAGO", "Healthcare"),
    ("OPENAI SAN FRANCISCO", "Subscriptions"),
    ("THE HOME DEPOT #6572 FLOWER MOUND", "Shopping"),
    ("MERITAGE HOMES OF TEXA AUSTIN", "Utilities"),
    ("TX.GOV*SERVICEFEE-DIR", "Utilities"),
    ("GROOMING PLACE FLOWER MOUND", "Healthcare"),
    ("PLAYGROUND AI SAN FRANCISCO", "Subscriptions"),
    ("5776 GREAT CLIPS AT MA FLOWER MOUND", "Healthcare"),
]

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def test_local_embeddings():
    """Test with sentence-transformers (local)"""
    from sentence_transformers import SentenceTransformer
    print("\n🔷 Testing LOCAL Model: sentence-transformers/all-MiniLM-L6-v2")
    
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    category_embeddings = model.encode(list(CATEGORIES.values()))
    
    results = []
    for merchant, expected in MERCHANTS:
        merchant_emb = model.encode(merchant)
        similarities = [cosine_similarity(merchant_emb, cat_emb) for cat_emb in category_embeddings]
        best_idx = np.argmax(similarities)
        best_category = list(CATEGORIES.keys())[best_idx]
        best_score = similarities[best_idx]
        correct = best_category == expected
        results.append((merchant[:30], best_category, best_score, correct, expected))
    
    return results

def test_openai_embeddings():
    """Test with OpenAI embeddings"""
    from openai import OpenAI
    print("\n🔶 Testing OPENAI Model: text-embedding-3-small")
    
    if not OPENAI_API_KEY:
        print("  ❌ OPENAI_API_KEY not found")
        return None
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    def get_embedding(text):
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    # Get category embeddings
    category_embeddings = [get_embedding(desc) for desc in CATEGORIES.values()]
    
    results = []
    for merchant, expected in MERCHANTS:
        merchant_emb = get_embedding(merchant)
        similarities = [cosine_similarity(np.array(merchant_emb), np.array(cat_emb)) for cat_emb in category_embeddings]
        best_idx = np.argmax(similarities)
        best_category = list(CATEGORIES.keys())[best_idx]
        best_score = similarities[best_idx]
        correct = best_category == expected
        results.append((merchant[:30], best_category, best_score, correct, expected))
    
    return results

def test_gemini_embeddings():
    """Test with Gemini embeddings"""
    import google.generativeai as genai
    print("\n🔵 Testing GEMINI Model: text-embedding-004")
    
    if not GEMINI_API_KEY:
        print("  ❌ GEMINI_API_KEY not found")
        return None
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    def get_embedding(text):
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text
        )
        return result['embedding']
    
    # Get category embeddings
    category_embeddings = [get_embedding(desc) for desc in CATEGORIES.values()]
    
    results = []
    for merchant, expected in MERCHANTS:
        merchant_emb = get_embedding(merchant)
        similarities = [cosine_similarity(np.array(merchant_emb), np.array(cat_emb)) for cat_emb in category_embeddings]
        best_idx = np.argmax(similarities)
        best_category = list(CATEGORIES.keys())[best_idx]
        best_score = similarities[best_idx]
        correct = best_category == expected
        results.append((merchant[:30], best_category, best_score, correct, expected))
    
    return results

def print_results(results, model_name):
    if not results:
        return
    
    print(f"\n{'Merchant':<32} {'Predicted':<15} {'Expected':<15} {'Score':<8} {'Match'}")
    print("-" * 85)
    
    correct_count = 0
    for merchant, predicted, score, correct, expected in results:
        status = "✓" if correct else "✗"
        if correct:
            correct_count += 1
        print(f"{merchant:<32} {predicted:<15} {expected:<15} {score:.3f}    {status}")
    
    accuracy = correct_count / len(results) * 100
    print(f"\n📊 {model_name} Accuracy: {correct_count}/{len(results)} ({accuracy:.0f}%)")
    return accuracy

def main():
    print("=" * 85)
    print("        EMBEDDING MODEL COMPARISON FOR TRANSACTION CATEGORIZATION")
    print("=" * 85)
    
    accuracies = {}
    
    # Test all three models
    local_results = test_local_embeddings()
    acc = print_results(local_results, "LOCAL")
    if acc: accuracies['Local (MiniLM)'] = acc
    
    openai_results = test_openai_embeddings()
    acc = print_results(openai_results, "OPENAI")
    if acc: accuracies['OpenAI'] = acc
    
    gemini_results = test_gemini_embeddings()
    acc = print_results(gemini_results, "GEMINI")
    if acc: accuracies['Gemini'] = acc
    
    # Summary comparison
    print("\n" + "=" * 85)
    print("                        SUMMARY COMPARISON")
    print("=" * 85)
    print(f"\n{'Model':<25} {'Accuracy':<15} {'Cost':<20}")
    print("-" * 60)
    print(f"{'Local (MiniLM-L6-v2)':<25} {accuracies.get('Local (MiniLM)', 'N/A'):.0f}%           {'Free (local)':<20}")
    print(f"{'OpenAI (text-emb-3-small)':<25} {accuracies.get('OpenAI', 'N/A'):.0f}%           {'~$0.00002/1K tokens':<20}")
    print(f"{'Gemini (text-emb-004)':<25} {accuracies.get('Gemini', 'N/A'):.0f}%           {'Free tier available':<20}")
    
    # Recommendation
    print("\n💡 RECOMMENDATION:")
    if accuracies:
        best = max(accuracies, key=accuracies.get)
        print(f"   Best performer: {best} with {accuracies[best]:.0f}% accuracy")
        if accuracies.get('Gemini', 0) >= accuracies.get('OpenAI', 0):
            print("   → Gemini has free tier, recommend for cost savings")
        elif accuracies.get('OpenAI', 0) > 70:
            print("   → OpenAI embedding quality is excellent for this use case")

if __name__ == "__main__":
    main()
