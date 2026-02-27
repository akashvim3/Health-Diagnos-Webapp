"""
Health Diagnosis Chatbot - Main Application
Professional Flask application with authentication and database integration
"""
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config
from database.models import db, User, ChatSession, ChatMessage, HealthRecord, SymptomRecord
from database.utils import create_user, create_chat_session, add_chat_message, get_user_chat_history
import openai
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    """Application factory pattern for creating Flask app"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Configure OpenAI
    openai.api_key = Config.OPENAI_API_KEY
    
    # Set up login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login"""
        return User.query.get(int(user_id))
    
    # Register blueprints
    from routes.chat_routes import chat_bp
    from routes.dashboard_routes import dashboard_bp
    from routes.auth_routes import auth_bp
    
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Home route
    @app.route('/')
    def index():
        """Home page with landing section"""
        return render_template('index.html')
    
    @app.route('/about')
    def about():
        """About page"""
        return render_template('about.html')
    
    @app.route('/features')
    def features():
        """Features page"""
        return render_template('features.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors"""
        return render_template('error.html', error_code=404, error_message='Page not found'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        db.session.rollback()
        return render_template('error.html', error_code=500, error_message='Internal server error'), 500
    
    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        """API health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'Health Diagnosis Chatbot',
            'version': '1.0.0'
        })
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create a demo user if none exists
        if not User.query.first():
            demo_user = User(
                email='demo@healthchatbot.com',
                username='demo_user'
            )
            demo_user.set_password('demo123')
            db.session.add(demo_user)
            db.session.commit()
            print("Demo user created: demo@healthchatbot.com / demo123")
    
    return app


# Application instance for WSGI
app = create_app()


if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
