#!/bin/bash

# Personal Finance Planner - Setup Script
# This script helps set up the local environment

echo "🚀 Personal Finance Planner - Setup Script"
echo "=========================================="

# Check Python version
echo ""
echo "📌 Checking Python version..."
python3 --version || {
    echo "❌ Python 3 is not installed"
    exit 1
}

# Check Node.js version
echo ""
echo "📌 Checking Node.js version..."
node --version || {
    echo "❌ Node.js is not installed"
   exit 1
}

# Create .env file
echo ""
echo "📌 Setting up environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env file from .env.example"
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
else
    echo "✅ .env file already exists"
fi

# Create data directories
echo ""
echo "📌 Creating data directories..."
mkdir -p data/chromadb data/uploads
echo "✅ Data directories created"

# Setup backend
echo ""
echo "📌 Setting up backend..."
cd backend || exit 1

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

echo "Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate 2>/dev/null

echo "Installing Python dependencies..."
pip install -r requirements.txt
echo "✅ Backend dependencies installed"

cd ..

# Setup frontend
echo ""
echo "📌 Setting up frontend..."
cd frontend || exit 1

if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
    echo "✅ Frontend dependencies installed"
else
    echo "✅ Frontend dependencies already installed"
fi

cd ..

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env and add your OPENAI_API_KEY"
echo "2. Start the backend:"
echo "   cd backend && source venv/bin/activate && python -m uvicorn main:app --reload"
echo "3. Start the frontend (in another terminal):"
echo "   cd frontend && npm run dev"
echo ""
echo "4. Open http://localhost:3000 in your browser"
echo "5. API docs: http://localhost:8000/docs"
echo ""
echo "Or use Docker:"
echo "   docker-compose up --build"
