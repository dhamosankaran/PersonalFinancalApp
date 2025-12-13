-- Database schema for Personal Finance Planner
-- PostgreSQL version (for SQLite, adjust UUID and JSONB types)

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    parent_id UUID REFERENCES categories(id),
    color VARCHAR(7),
    icon VARCHAR(50)
);

CREATE INDEX idx_categories_name ON categories(name);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_date DATE NOT NULL,
    merchant VARCHAR(255),
    amount DECIMAL(10, 2) NOT NULL,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    description TEXT,
    source_file VARCHAR(255),
    is_recurring BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_transactions_merchant ON transactions(merchant);
CREATE INDEX idx_transactions_recurring ON transactions(is_recurring);

-- Uploaded documents table
CREATE TABLE IF NOT EXISTS uploaded_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    processed BOOLEAN DEFAULT FALSE,
    transaction_count INTEGER DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_user_id ON uploaded_documents(user_id);
CREATE INDEX idx_documents_processed ON uploaded_documents(processed);

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    retrieved_context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_user_id ON chat_messages(user_id);
CREATE INDEX idx_chat_created_at ON chat_messages(created_at);

-- Insert default categories
INSERT INTO categories (name, color, icon) VALUES
    ('Food & Dining', '#FF6B6B', 'utensils'),
    ('Groceries', '#4ECDC4', 'shopping-cart'),
    ('Transportation', '#45B7D1', 'car'),
    ('Shopping', '#FFA07A', 'shopping-bag'),
    ('Entertainment', '#98D8C8', 'film'),
    ('Utilities', '#6C5CE7', 'zap'),
    ('Healthcare', '#A8E6CF', 'heart'),
    ('Travel', '#FFD93D', 'plane'),
    ('Subscriptions', '#BC85A3', 'repeat'),
    ('Uncategorized', '#95A5A6', 'help-circle')
ON CONFLICT (name) DO NOTHING;
