import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Base configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    # Email configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@richainfosys.com')
    
    # CORS settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')

class DevelopmentConfig(Config):
    DEBUG = True
    CORS_ORIGINS = ['http://localhost:3000']  # React's default port

class ProductionConfig(Config):
    DEBUG = False
    CORS_ORIGINS = ['https://your-production-domain.com']

# Dictionary to map config names to classes
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
