"""
Configuration module for the Personal Finance Planner backend.
Loads environment variables and provides application settings.
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = Field(
        default="sqlite:///./data/finance.db",
        description="Database connection URL"
    )
    
    # OpenAI
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key for LLM reasoning"
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use"
    )
    
    # Google Gemini
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key for LLM reasoning"
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash-lite",
        description="Gemini model to use"
    )
    
    # LLM Provider Settings
    default_llm_provider: str = Field(
        default="openai",
        description="Default LLM provider (openai or gemini)"
    )
    
    # Server
    backend_port: int = Field(default=8000, description="Backend server port")
    backend_host: str = Field(default="0.0.0.0", description="Backend server host")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        description="Comma-separated CORS origins"
    )
    
    # Embeddings
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Local embedding model"
    )
    embedding_device: str = Field(
        default="cpu",
        description="Device for embeddings (cpu/cuda)"
    )
    
    # ChromaDB
    chroma_persist_directory: str = Field(
        default="./data/chromadb",
        description="ChromaDB persistence directory"
    )
    
    # DuckDB
    duckdb_path: str = Field(
        default="./data/analytics.duckdb",
        description="DuckDB database path"
    )
    
    # File Upload
    upload_directory: str = Field(
        default="./data/uploads",
        description="Directory for uploaded files"
    )
    max_upload_size: int = Field(
        default=10485760,  # 10MB
        description="Maximum upload size in bytes"
    )
    
    # Statements Directory (for RAG processing)
    statements_directory: str = Field(
        default="./statements",
        description="Directory containing financial statements for RAG processing"
    )
    
    # OCR
    tesseract_path: str = Field(
        default="/usr/local/bin/tesseract",
        description="Path to Tesseract executable"
    )
    
    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time"
    )
    
    class Config:
        # Try both locations for .env file
        env_file = ".env"  # When running from project root
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Load from explicit path if env_file doesn't work
import os
from pathlib import Path

def _find_env_file():
    """Find the .env file in the project."""
    # Check current directory
    if os.path.exists(".env"):
        return ".env"
    # Check parent directory
    if os.path.exists("../.env"):
        return "../.env"
    # Check relative to this file
    config_dir = Path(__file__).parent
    project_root = config_dir.parent
    if (project_root / ".env").exists():
        return str(project_root / ".env")
    return ".env"

# Global settings instance
from dotenv import load_dotenv
load_dotenv(_find_env_file())
settings = Settings()

