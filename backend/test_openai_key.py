#!/usr/bin/env python3
"""
Test script to verify OpenAI API key is correctly configured.
Run from the backend directory with the virtual environment activated:
    python test_openai_key.py
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env from parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

def test_openai_key():
    """Test the OpenAI API key by making a simple API call."""
    
    # Check if API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ OPENAI_API_KEY is not set in the environment.")
        print(f"   Please add it to: {env_path}")
        return False
    
    if api_key.startswith("sk-") is False and api_key.startswith("sk-proj-") is False:
        print("⚠️  Warning: API key format may be incorrect.")
        print("   OpenAI keys typically start with 'sk-' or 'sk-proj-'")
    
    print(f"✅ OPENAI_API_KEY found (length: {len(api_key)} chars)")
    print(f"   Key prefix: {api_key[:10]}...")
    
    # Try to import and use the OpenAI client
    try:
        from openai import OpenAI
        print("\n🔄 Testing API connection...")
        
        client = OpenAI(api_key=api_key)
        
        # Make a simple API call to list models
        response = client.models.list()
        
        # Get a few model names
        model_names = [model.id for model in response.data[:5]]
        
        print("✅ API connection successful!")
        print(f"   Available models (first 5): {', '.join(model_names)}")
        
        # Optional: Test a simple completion
        print("\n🔄 Testing chat completion...")
        
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say 'API test successful!' in 5 words or less."}
            ],
            max_tokens=20
        )
        
        response_text = completion.choices[0].message.content
        print(f"✅ Chat completion successful!")
        print(f"   Response: {response_text}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import OpenAI library: {e}")
        print("   Run: pip install openai")
        return False
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("OpenAI API Key Test")
    print("=" * 50)
    print()
    
    success = test_openai_key()
    
    print()
    print("=" * 50)
    if success:
        print("✅ All tests passed! Your OpenAI API key is working.")
    else:
        print("❌ Tests failed. Please check your configuration.")
    print("=" * 50)
    
    sys.exit(0 if success else 1)
