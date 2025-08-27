from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and profile information"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    chat_sessions = db.relationship('ChatSession', backref='user', lazy=True)
    health_records = db.relationship('HealthRecord', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ChatSession(db.Model):
    """Model for storing chat sessions"""
    __tablename__ = 'chat_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    
    # Relationships
    messages = db.relationship('ChatMessage', backref='session', lazy=True)
    symptoms = db.relationship('SymptomRecord', backref='session', lazy=True)

class ChatMessage(db.Model):
    """Model for storing individual chat messages"""
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    message_type = db.Column(db.String(10), nullable=False)  # 'user' or 'ai'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Optional metadata
    detected_symptoms = db.Column(db.JSON)
    suggested_conditions = db.Column(db.JSON)
    confidence_score = db.Column(db.Float)

class HealthRecord(db.Model):
    """Model for storing user health records and history"""
    __tablename__ = 'health_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    # Health data
    conditions = db.Column(db.JSON)  # List of diagnosed conditions
    medications = db.Column(db.JSON)  # List of medications
    allergies = db.Column(db.JSON)  # List of allergies
    chronic_conditions = db.Column(db.JSON)  # List of chronic conditions

class SymptomRecord(db.Model):
    """Model for tracking reported symptoms"""
    __tablename__ = 'symptom_records'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    symptom_name = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.Integer)  # 1-5 scale
    duration = db.Column(db.String(50))  # e.g., "2 days", "1 week"
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Metadata
    extracted_by = db.Column(db.String(50))  # e.g., "user_input", "ai_analysis"
    confidence_score = db.Column(db.Float)

class EmergencyContact(db.Model):
    """Model for storing emergency contact information"""
    __tablename__ = 'emergency_contacts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.String(50))
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    is_primary = db.Column(db.Boolean, default=False)

class HealthMetrics(db.Model):
    """Model for tracking health metrics over time"""
    __tablename__ = 'health_metrics'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)  # e.g., "blood_pressure", "temperature"
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)  # e.g., "mmHg", "celsius"
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Optional metadata
    notes = db.Column(db.Text)
    source = db.Column(db.String(50))  # e.g., "user_input", "device_sync"

class MedicalReport(db.Model):
    """Model for storing generated medical reports"""
    __tablename__ = 'medical_reports'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)  # e.g., "symptom_analysis", "health_summary"
    content = db.Column(db.JSON, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Report metadata
    format = db.Column(db.String(20))  # e.g., "pdf", "html"
    file_path = db.Column(db.String(255))
    is_archived = db.Column(db.Boolean, default=False)
