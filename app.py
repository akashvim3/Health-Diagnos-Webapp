from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    CORS(app)

    with app.app_context():
        # Import routes
        from routes.chat_routes import chat_bp
        from routes.dashboard_routes import dashboard_bp

        # Register blueprints
        app.register_blueprint(chat_bp)
        app.register_blueprint(dashboard_bp)

        # Create database tables
        db.create_all()

        return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
