#!/usr/bin/env python3
"""
Run the Personal Finance Planner backend server.
This script properly sets up the Python path for relative imports.
"""

import sys
import os

# Add parent directory to path for proper module resolution
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
sys.path.insert(0, parent_dir)

# Now change the imports in main.py to work as a package
os.chdir(backend_dir)

# Load environment from parent .env
from dotenv import load_dotenv
load_dotenv(os.path.join(parent_dir, '.env'))

if __name__ == "__main__":
    import uvicorn
    
    # Import settings after dotenv is loaded
    from config import settings
    
    print("Starting Personal Finance Planner API...")
    print(f"Server: http://{settings.backend_host}:{settings.backend_port}")
    print(f"API Docs: http://localhost:{settings.backend_port}/docs")
    
    uvicorn.run(
        "app:app",  # Will use app.py
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True
    )
