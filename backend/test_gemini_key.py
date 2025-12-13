#!/usr/bin/env python3
"""
Test script to verify Gemini API key is correctly configured.
Run from the backend directory with the virtual environment activated:
    python test_gemini_key.py
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env from parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def test_gemini_key():
    """Test the Gemini API key by making a simple API call."""
    
    # Check if API key is set (try both common env var names)
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    key_name = "GEMINI_API_KEY" if os.getenv("GEMINI_API_KEY") else "GOOGLE_API_KEY"
    
    if not api_key:
        print("❌ GEMINI_API_KEY or GOOGLE_API_KEY is not set in the environment.")
        print(f"   Please add it to: {env_path}")
        print("   Expected format: GEMINI_API_KEY=your_api_key_here")
        return False
    
    print(f"✅ {key_name} found (length: {len(api_key)} chars)")
    print(f"   Key prefix: {api_key[:10]}...")
    
    # Try to import and use the Google Generative AI client
    try:
        import google.generativeai as genai
        print("\n🔄 Testing API connection...")
        
        # Configure the API key
        genai.configure(api_key=api_key)
        
        # List available models
        print("🔄 Fetching available models...")
        models = list(genai.list_models())
        
        # Filter for Gemini models that support generateContent
        gemini_models = [
            m.name for m in models 
            if 'generateContent' in m.supported_generation_methods
        ][:5]
        
        print("✅ API connection successful!")
        print(f"   Available Gemini models (first 5): {', '.join(gemini_models)}")
        
        # Test a simple generation
        print("\n🔄 Testing text generation...")
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            "Say 'API test successful!' in 5 words or less.",
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=50,
                temperature=0.1
            )
        )
        
        response_text = response.text.strip()
        print(f"✅ Text generation successful!")
        print(f"   Response: {response_text}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import Google Generative AI library: {e}")
        print("   Run: pip install google-generativeai")
        return False
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        if "API_KEY_INVALID" in str(e):
            print("   Your API key appears to be invalid. Please verify it in Google AI Studio.")
        elif "quota" in str(e).lower():
            print("   You may have exceeded your API quota.")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Gemini API Key Test")
    print("=" * 50)
    print()
    
    success = test_gemini_key()
    
    print()
    print("=" * 50)
    if success:
        print("✅ All tests passed! Your Gemini API key is working.")
    else:
        print("❌ Tests failed. Please check your configuration.")
    print("=" * 50)
    
    sys.exit(0 if success else 1)
