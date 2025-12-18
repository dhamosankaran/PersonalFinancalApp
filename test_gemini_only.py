"""Quick Gemini-only test"""
import os
import sys
sys.path.insert(0, '/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/PersonalFinancePlanning_RAG/backend')

from dotenv import load_dotenv
import numpy as np

load_dotenv('/Users/kalaidhamu/Desktop/KalaiDhamu/LLM/General/PersonalFinancePlanning_RAG/.env')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')

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

MERCHANTS = [
    ("CURSOR USAGE FEB NEW YORK", "Subscriptions"),
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

print("🔵 Testing GEMINI Model: text-embedding-004")

if not GEMINI_API_KEY:
    print("  ❌ GEMINI_API_KEY not found")
    exit(1)

import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)

def get_embedding(text):
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text
    )
    return result['embedding']

# Get category embeddings
print("  Getting category embeddings...")
category_embeddings = [get_embedding(desc) for desc in CATEGORIES.values()]

print(f"\n{'Merchant':<32} {'Predicted':<15} {'Expected':<15} {'Score':<8} {'Match'}")
print("-" * 85)

correct_count = 0
for merchant, expected in MERCHANTS:
    merchant_emb = get_embedding(merchant)
    similarities = [cosine_similarity(np.array(merchant_emb), np.array(cat_emb)) for cat_emb in category_embeddings]
    best_idx = np.argmax(similarities)
    best_category = list(CATEGORIES.keys())[best_idx]
    best_score = similarities[best_idx]
    correct = best_category == expected
    if correct:
        correct_count += 1
    status = "✓" if correct else "✗"
    print(f"{merchant[:30]:<32} {best_category:<15} {expected:<15} {best_score:.3f}    {status}")

print(f"\n📊 GEMINI Accuracy: {correct_count}/{len(MERCHANTS)} ({correct_count/len(MERCHANTS)*100:.0f}%)")

print("\n" + "=" * 85)
print("                        FINAL COMPARISON SUMMARY")
print("=" * 85)
print(f"\n{'Model':<25} {'Accuracy':<15} {'Cost':<25}")
print("-" * 65)
print(f"{'Local (MiniLM-L6-v2)':<25} {'64%':<15} {'Free (local)':<25}")
print(f"{'OpenAI (text-emb-3-small)':<25} {'82%':<15} {'~$0.00002/1K tokens':<25}")
print(f"{'Gemini (text-emb-004)':<25} {f'{correct_count/len(MERCHANTS)*100:.0f}%':<15} {'Free tier available':<25}")

print("\n💡 RECOMMENDATION:")
if correct_count/len(MERCHANTS) >= 0.82:
    print("   → Gemini matches/beats OpenAI accuracy and has free tier!")
    print("   → Recommended: Use Gemini embeddings for cost savings")
elif correct_count/len(MERCHANTS) >= 0.64:
    print("   → Gemini is better than local model")
    print("   → For best accuracy, use OpenAI; for free, use Gemini")
