import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(os.path.dirname(basedir), ".env"))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-placeholder")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    GMAIL_SENDER = os.environ.get("GMAIL_SENDER")
    GMAIL_APP_PASS = os.environ.get("GMAIL_APP_PASS")
    
    # LLM Config
    USE_OPENAI = os.environ.get("USE_OPENAI", "false").lower() == "true"
    LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
    LLM_MODEL = os.environ.get("LLM_MODEL", "llama3.2")
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "ollama")
    
    # Database (Migration to SQLAlchemy will use this)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        'sqlite:///' + os.path.join(os.path.dirname(basedir), 'data.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
