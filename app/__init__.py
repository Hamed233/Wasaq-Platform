from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from config import config
import datetime

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
csrf = CSRFProtect()

def create_app(config_name):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    CORS(app)
    
    # Ensure instance folder exists
    try:
        import os
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Register context processors
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.now()}
    
    # Register custom filters
    @app.template_filter('without')
    def without_url_param(d, param):
        if not d:
            return {}
        new_d = d.copy()
        if param in new_d:
            new_d.pop(param)
        return new_d
    
    # Register blueprints
    from app.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from app.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    from app.api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    from app.dashboard import dashboard as dashboard_blueprint
    app.register_blueprint(dashboard_blueprint, url_prefix='/dashboard')
    
    from app.lands import lands as lands_blueprint
    app.register_blueprint(lands_blueprint, url_prefix='/lands')
    
    from app.reports import reports as reports_blueprint
    app.register_blueprint(reports_blueprint, url_prefix='/reports')
    
    from app.chatbot import chatbot as chatbot_blueprint
    app.register_blueprint(chatbot_blueprint, url_prefix='/chatbot')
    
    return app
