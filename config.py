import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///database/health.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes
    
    # Security Configuration
    CORS_HEADERS = 'Content-Type'
    
    # Model Configuration
    MODEL_PATH = 'models/'
    SYMPTOM_EXTRACTOR_MODEL = 'biobert-v1.1'  # or your chosen model
    
    # Chat Configuration
    MAX_CHAT_HISTORY = 10  # Number of messages to keep in context
    EMERGENCY_KEYWORDS = ['emergency', 'severe pain', 'unconscious', 'difficulty breathing']
