import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'waqaf.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # GIS settings
    MAP_CENTER_LAT = 24.7136  # Saudi Arabia center latitude
    MAP_CENTER_LNG = 46.6753  # Saudi Arabia center longitude
    MAP_DEFAULT_ZOOM = 6
    
    # Pagination settings
    LANDS_PER_PAGE = 9
    REPORTS_PER_PAGE = 10
    RECOMMENDATIONS_PER_PAGE = 10
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # API keys and external services
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Chatbot settings
    CHATBOT_NAME = 'WaqafBot'
    CHATBOT_LANGUAGE = 'ar'  # Arabic
    
    # Blockchain settings (placeholder for future implementation)
    BLOCKCHAIN_ENABLED = False
    
    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


class ProductionConfig(Config):
    DEBUG = False
    # Use PostgreSQL in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://user:password@localhost/waqaf'


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
