# Personal Finance Planner with RAG & Agentic AI

A **local-first** personal finance management system that uses RAG (Retrieval-Augmented Generation) for intelligent financial insights and will support agentic AI for automated budgeting, subscription audits, and savings optimization.

## 🎯 Project Vision

Analyze 12 months of credit card statements, extract transactions, categorize spending, identify patterns, and provide AI-powered insights — all while keeping your data 100% local except for final LLM reasoning calls.

## ✨ Features

### Phase 1: Personal Finance Analyzer (IMPLEMENTED ✅)

#### ✅ Backend Infrastructure
- **FastAPI** REST API with asynchronous support
- **PostgreSQL/SQLite** for structured transaction storage
- **DuckDB** for fast analytical queries
- **ChromaDB** for local vector storage (100% privacy)
- **Sentence-transformers** for local embeddings
- **LangChain + OpenAI** for RAG-based insights

#### ✅ PDF/CSV Processing
- PDFPlumber for digital PDFs
- PyMuPDF fallback for complex layouts
- Tesseract OCR for image-only PDFs
- CSV parser with dialect detection
- Auto-categorization (rule-based + LLM refinement)

#### ✅ RAG Pipeline
- Local embedding generation (sentence-transformers)
- Vector indexing with ChromaDB
- Context retrieval for questions like:
  - "How much did I spend on groceries last month?"
  - "What are my top 10 merchants this year?"
  - "Where can I reduce expenses?"

#### ✅ Analytics Endpoints
- Monthly spend breakdown
- Category-wise analysis
- Top merchants by spending
- Recurring subscription detection
- AI-generated savings insights

### Phase 2: Agentic AI (PLANNED 🚧)

The following AI agents will be implemented using LangGraph:

1. **Budget Planning Agent** - Creates and monitors monthly budgets
2. **Subscription Auditor** - Detects unused subscriptions
3. **Savings Optimizer** - Identifies cost-cutting opportunities
4. **Anomaly Detector** - Flags suspicious transactions

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│  Dashboard | Upload | Transactions | Chat | Analytics        │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────┴──────────────────────────────────┐
│                    Backend (FastAPI)                         │
├──────────────────────────────────────────────────────────────┤
│  Routers: Upload | Transactions | Chat | Analytics           │
├──────────────────────────────────────────────────────────────┤
│  Services:                                                    │
│    • Document Processor (PDF/CSV)                            │
│    • Categorizer (Rule-based + LLM)                          │
│    • Embedding Service (sentence-transformers) 🔒 LOCAL      │
│    • Vector Store (ChromaDB) 🔒 LOCAL                        │
│    • RAG Service (LangChain + OpenAI)                        │
│    • Analytics (DuckDB)                                      │
└──────────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────┐
│                    Data Layer                                │
├──────────────────────────────────────────────────────────────┤
│  PostgreSQL/SQLite  │  ChromaDB  │  DuckDB                   │
│  (Transactions)     │  (Vectors) │  (Analytics)               │
└──────────────────────────────────────────────────────────────┘
                           │
                  🔒 100% Local Processing
                  ☁️ Only LLM reasoning → OpenAI
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Docker & Docker Compose** (optional)
- **OpenAI API Key** (for LLM reasoning)

### Option 1: Local Setup

#### 1. Clone and Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example .env
# Edit .env and add your OPENAI_API_KEY
```

#### 2. Run Backend

```bash
# From backend directory
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000/docs` (OpenAPI documentation).

#### 3. Setup & Run Frontend

```bash
cd frontend

# Install dependencies (if not already done)
npm install

# Run development server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### Option 2: Docker Setup

```bash
# Copy environment file
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start all services
docker-compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## 📁 Project Structure

```
PersonalFinancePlanning_RAG/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings
│   ├── database.py             # SQLAlchemy setup
│   ├── models/                 # Database models
│   │   ├── user.py
│   │   ├── transaction.py
│   │   ├── document.py
│   │   └── chat.py
│   ├── schemas/                # Pydantic schemas
│   │   ├── transaction.py
│   │   ├── chat.py
│   │   └── analytics.py
│   ├── services/               # Business logic
│   │   ├── document_processor.py     # PDF/CSV extraction
│   │   ├── categorizer.py            # Transaction categorization
│   │   ├── embeddings.py             # Local embeddings
│   │   ├── vector_store.py           # ChromaDB integration
│   │   ├── rag_service.py            # RAG pipeline
│   │   └── analytics.py              # DuckDB analytics
│   ├── routers/                # API endpoints
│   │   ├── upload.py
│   │   ├── transactions.py
│   │   ├── chat.py
│   │   └── analytics.py
│   └── requirements.txt
├── frontend/
│   ├── app/                    # Next.js 14 App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx            # Dashboard
│   │   ├── upload/
│   │   ├── transactions/
│   │   ├── chat/
│   │   └── analytics/
│   ├── components/             # React components
│   │   ├── ui/
│   │   ├── upload/
│   │   ├── transactions/
│   │   ├── chat/
│   │   └── analytics/
│   ├── utils/
│   │   └── api.ts              # API client
│   └── package.json
├── database/
│   └── schema.sql              # Database schema
├── docker-compose.yml
└── .env.example
```

---

## 🔌 API Endpoints

### Upload
- `POST /api/upload/` - Upload PDF/CSV file
- `GET /api/upload/documents` - List uploaded documents

### Transactions
- `GET /api/transactions/` - List transactions (with filters)
- `POST /api/transactions/` - Create transaction
- `PUT /api/transactions/{id}` - Update transaction
- `DELETE /api/transactions/{id}` - Delete transaction

### Chat (RAG)
- `POST /api/chat/` - Send message, get AI response
- `GET /api/chat/history` - Get conversation history
- `DELETE /api/chat/history` - Clear history

### Analytics
- `GET /api/analytics/monthly?months=12` - Monthly spend
- `GET /api/analytics/category?months=12` - Category breakdown
- `GET /api/analytics/merchants?months=12&limit=10` - Top merchants
- `GET /api/analytics/subscriptions` - Recurring subscriptions
- `GET /api/analytics/insights` - AI-generated insights

---

## 🔒 Privacy & Security

### ✅ What Stays Local
- **All PDFs and CSV files** - Stored locally, never uploaded
- **All transactions** - Stored in local database
- **All embeddings** - Generated locally using sentence-transformers
- **All vector data** - Stored in local ChromaDB instance
- **All analytics** - Processed locally with DuckDB

### ☁️ What Goes to OpenAI
- **Only**: Retrieved context chunks + user question
- **Never**: Raw PDFs, full transaction lists, or sensitive data
- **Why**: Final LLM reasoning for natural language responses

---

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for PostgreSQL/SQLite
- **Pandas & Polars** - Data manipulation
- **DuckDB** - Fast analytical queries
- **ChromaDB** - Local vector store
- **Sentence-Transformers** - Local embeddings
- **LangChain** - RAG orchestration
- **PDFPlumber & PyMuPDF** - PDF extraction
- **Tesseract** - OCR fallback

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Recharts** - Data visualization
- **TanStack Query** - Server state management
- **Axios** - API client

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **PostgreSQL** - Relational database
- **ChromaDB** - Vector database

---

## 📊 Example Queries

Once you've uploaded your credit card statements, you can ask:

- "What are my top 10 merchants this year?"
- "How much did I spend on groceries last month?"
- "Show me all travel expenses from June to September"
- "Where can I reduce my expenses?"
- "What recurring subscriptions am I paying for?"
- "Compare my spending this month vs last month"
- "What percentage of my budget goes to dining out?"

---

## 🗺️ Roadmap

### ✅ Phase 1: Personal Finance Analyzer (COMPLETE)
- [x] PDF/CSV processing
- [x] Transaction extraction & categorization
- [x] RAG pipeline
- [x] Chat interface
- [x] Analytics dashboards
- [x] Backend API

### 🚧 Phase 2: Frontend Development (IN PROGRESS)
- [ ] Dashboard UI
- [ ] Upload interface
- [ ] Transaction management
- [ ] Chat UI
- [ ] Analytics visualizations

### 📋 Phase 3: Agentic AI (PLANNED)
- [ ] Budget Planning Agent
- [ ] Subscription Auditor Agent
- [ ] Savings Optimization Agent
- [ ] Anomaly Detection Agent

---

## 🤝 Contributing

This is a personal project, but suggestions and feedback are welcome!

---

## 📜 License

MIT License - feel free to use for personal projects.

---

## 🙋 Support

For issues or questions:
1. Check the API docs at `http://localhost:8000/docs`
2. Review the implementation plan in `/brain/implementation_plan.md`
3. Check task progress in `/brain/task.md`

---

**Built with ❤️ using local-first AI principles**
