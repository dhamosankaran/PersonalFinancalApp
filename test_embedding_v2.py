"""
Compare embedding models for transaction categorization:
1. Local: sentence-transformers/all-MiniLM-L6-v2
2. Gemini: embedding-001
3. OpenAI: text-embedding-3-large

Run: python test_embedding_v2.py
"""

import os
import sys
import time
sys.path.insert(0, '/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/PersonalFinancePlanning_RAG/backend')

from dotenv import load_dotenv
import numpy as np

load_dotenv('/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/PersonalFinancePlanning_RAG/.env')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')

# Categories with rich descriptions
CATEGORIES = {
    "Food & Dining": "restaurant cafe coffee pizza burger food dining bar grill kitchen eating out meals takeout delivery",
    "Groceries": "grocery store supermarket whole foods trader joe walmart target costco food shopping produce market",
    "Transportation": "uber lyft taxi gas fuel shell chevron exxon parking toll transit ride car driving ntta tollway",
    "Shopping": "amazon retail store mall purchase buy merchandise goods clothing electronics home depot hardware lowes",
    "Entertainment": "netflix spotify movie theater cinema concert game streaming music video gaming arcade",
    "Utilities": "electric gas water internet cable phone utility power energy bill payment service provider att verizon",
    "Healthcare": "pharmacy cvs walgreens hospital clinic doctor medical health dental vision pet insurance grooming salon haircut spa",
    "Travel": "airline hotel airbnb flight booking vacation trip southwest delta united american",
    "Subscriptions": "subscription monthly membership software service cloud platform hosting SaaS AI cursor openai google cloud adobe",
}

# Test merchants with expected categories
MERCHANTS = [
    ("CURSOR USAGE FEB NEW YORK", "Subscriptions"),
    ("GOOGLE *CLOUD NMxVBL", "Subscriptions"),
    ("NTTA ONLINE", "Transportation"),  # Toll road
    ("FIGO PET INS CHICAGO", "Healthcare"),
    ("OPENAI SAN FRANCISCO", "Subscriptions"),
    ("THE HOME DEPOT #6572 FLOWER MOUND", "Shopping"),
    ("MERITAGE HOMES OF TEXA AUSTIN", "Utilities"),  # Home builder/mortgage
    ("TX.GOV*SERVICEFEE-DIR", "Utilities"),
    ("GROOMING PLACE FLOWER MOUND", "Healthcare"),
    ("PLAYGROUND AI SAN FRANCISCO", "Subscriptions"),
    ("5776 GREAT CLIPS AT MA FLOWER MOUND", "Healthcare"),
    ("CHICK-FIL-A APP ATLANTA", "Food & Dining"),
    ("KROGER #0585 FLOWER MOUND", "Groceries"),
    ("NETFLIX.COM", "Entertainment"),
    ("SOUTHWEST AIR", "Travel"),
]

def cosine_similarity(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def test_local():
    """Test with local sentence-transformers"""
    from sentence_transformers import SentenceTransformer
    print("\n🔷 LOCAL: sentence-transformers/all-MiniLM-L6-v2")
    print("   Dimension: 384 | Cost: FREE | Speed: Fast")
    print("-" * 75)
    
    start = time.time()
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
        results.append((merchant[:35], best_category, expected, best_score, correct))
    
    elapsed = time.time() - start
    return results, elapsed

def test_openai_large():
    """Test with OpenAI text-embedding-3-large"""
    from openai import OpenAI
    print("\n🔶 OPENAI: text-embedding-3-large")
    print("   Dimension: 3072 | Cost: $0.00013/1K tokens | Speed: Medium")
    print("-" * 75)
    
    if not OPENAI_API_KEY:
        print("   ❌ OPENAI_API_KEY not found")
        return None, 0
    
    start = time.time()
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    def get_embedding(text):
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input=text
        )
        return response.data[0].embedding
    
    category_embeddings = [get_embedding(desc) for desc in CATEGORIES.values()]
    
    results = []
    for merchant, expected in MERCHANTS:
        merchant_emb = get_embedding(merchant)
        similarities = [cosine_similarity(np.array(merchant_emb), np.array(cat_emb)) for cat_emb in category_embeddings]
        best_idx = np.argmax(similarities)
        best_category = list(CATEGORIES.keys())[best_idx]
        best_score = similarities[best_idx]
        correct = best_category == expected
        results.append((merchant[:35], best_category, expected, best_score, correct))
    
    elapsed = time.time() - start
    return results, elapsed

def test_gemini():
    """Test with Gemini embedding-001"""
    import google.generativeai as genai
    print("\n🔵 GEMINI: embedding-001")
    print("   Dimension: 768 | Cost: FREE (quota) | Speed: Medium")
    print("-" * 75)
    
    if not GEMINI_API_KEY:
        print("   ❌ GEMINI_API_KEY not found")
        return None, 0
    
    start = time.time()
    genai.configure(api_key=GEMINI_API_KEY)
    
    def get_embedding(text):
        result = genai.embed_content(
            model="models/embedding-001",
            content=text
        )
        return result['embedding']
    
    category_embeddings = [get_embedding(desc) for desc in CATEGORIES.values()]
    
    results = []
    for merchant, expected in MERCHANTS:
        merchant_emb = get_embedding(merchant)
        similarities = [cosine_similarity(np.array(merchant_emb), np.array(cat_emb)) for cat_emb in category_embeddings]
        best_idx = np.argmax(similarities)
        best_category = list(CATEGORIES.keys())[best_idx]
        best_score = similarities[best_idx]
        correct = best_category == expected
        results.append((merchant[:35], best_category, expected, best_score, correct))
    
    elapsed = time.time() - start
    return results, elapsed

def print_results(results, model_name):
    if not results:
        return 0, 0
    
    print(f"\n{'Merchant':<37} {'Predicted':<15} {'Expected':<15} {'Score':<7} {'OK'}")
    print("-" * 85)
    
    correct = 0
    high_conf = 0
    for merchant, predicted, expected, score, is_correct in results:
        status = "✓" if is_correct else "✗"
        if is_correct:
            correct += 1
        if score > 0.35:
            high_conf += 1
        print(f"{merchant:<37} {predicted:<15} {expected:<15} {score:.3f}   {status}")
    
    accuracy = correct / len(results) * 100
    return correct, accuracy

def main():
    print("=" * 85)
    print("      EMBEDDING MODEL COMPARISON: Local vs OpenAI-Large vs Gemini-001")
    print("=" * 85)
    
    all_results = {}
    
    # Test Local
    results, elapsed = test_local()
    correct, acc = print_results(results, "LOCAL")
    all_results['Local (MiniLM)'] = {'correct': correct, 'accuracy': acc, 'time': elapsed}
    print(f"\n📊 Accuracy: {correct}/{len(MERCHANTS)} ({acc:.0f}%) | Time: {elapsed:.2f}s")
    
    # Test OpenAI Large
    results, elapsed = test_openai_large()
    if results:
        correct, acc = print_results(results, "OPENAI")
        all_results['OpenAI (3-large)'] = {'correct': correct, 'accuracy': acc, 'time': elapsed}
        print(f"\n📊 Accuracy: {correct}/{len(MERCHANTS)} ({acc:.0f}%) | Time: {elapsed:.2f}s")
    
    # Test Gemini
    results, elapsed = test_gemini()
    if results:
        correct, acc = print_results(results, "GEMINI")
        all_results['Gemini (001)'] = {'correct': correct, 'accuracy': acc, 'time': elapsed}
        print(f"\n📊 Accuracy: {correct}/{len(MERCHANTS)} ({acc:.0f}%) | Time: {elapsed:.2f}s")
    
    # Summary
    print("\n" + "=" * 85)
    print("                           FINAL COMPARISON")
    print("=" * 85)
    print(f"\n{'Model':<22} {'Accuracy':<12} {'Time':<10} {'Dimension':<12} {'Cost'}")
    print("-" * 75)
    
    for model, data in all_results.items():
        dim = "384" if "MiniLM" in model else "3072" if "large" in model else "768"
        cost = "Free" if "Local" in model or "Gemini" in model else "$0.00013/1K"
        print(f"{model:<22} {data['accuracy']:.0f}%         {data['time']:.2f}s      {dim:<12} {cost}")
    
    print("\n💡 RECOMMENDATION:")
    best = max(all_results, key=lambda x: all_results[x]['accuracy'])
    print(f"   Best accuracy: {best} with {all_results[best]['accuracy']:.0f}%")
    
    if 'Gemini' in all_results and 'OpenAI' in all_results:
        gemini_acc = all_results.get('Gemini (001)', {}).get('accuracy', 0)
        openai_acc = all_results.get('OpenAI (3-large)', {}).get('accuracy', 0)
        if gemini_acc >= openai_acc:
            print("   → Gemini matches/beats OpenAI and is FREE - recommended!")
        else:
            diff = openai_acc - gemini_acc
            print(f"   → OpenAI is {diff:.0f}% better but costs money")
            print(f"   → Consider Gemini if {diff:.0f}% difference is acceptable")

if __name__ == "__main__":
    main()
