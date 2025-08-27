"""Database initialization and utility functions"""
from flask import current_app
from database.models import db, User, ChatSession, ChatMessage, HealthRecord
from datetime import datetime

def init_db(app):
    """Initialize the database with the Flask app"""
    db.init_app(app)
    with app.app_context():
        db.create_all()

def create_user(email, username, password):
    """Create a new user"""
    user = User(email=email, username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user

def get_user_chat_history(user_id, limit=10):
    """Get recent chat history for a user"""
    return ChatSession.query.filter_by(user_id=user_id)\
        .order_by(ChatSession.started_at.desc())\
        .limit(limit)\
        .all()

def create_chat_session(user_id):
    """Create a new chat session"""
    session = ChatSession(user_id=user_id)
    db.session.add(session)
    db.session.commit()
    return session

def add_chat_message(session_id, message_type, content, symptoms=None, conditions=None):
    """Add a new message to a chat session"""
    message = ChatMessage(
        session_id=session_id,
        message_type=message_type,
        content=content,
        detected_symptoms=symptoms,
        suggested_conditions=conditions
    )
    db.session.add(message)
    db.session.commit()
    return message

def get_user_health_records(user_id):
    """Get health records for a user"""
    return HealthRecord.query.filter_by(user_id=user_id).first()

def update_health_record(user_id, data):
    """Update or create health record for a user"""
    record = HealthRecord.query.filter_by(user_id=user_id).first()
    if not record:
        record = HealthRecord(user_id=user_id)
    
    # Update fields
    for key, value in data.items():
        if hasattr(record, key):
            setattr(record, key, value)
    
    record.updated_at = datetime.utcnow()
    db.session.add(record)
    db.session.commit()
    return record

def add_symptom_record(session_id, symptom_data):
    """Add a new symptom record"""
    from database.models import SymptomRecord
    
    symptom = SymptomRecord(
        session_id=session_id,
        symptom_name=symptom_data['name'],
        severity=symptom_data.get('severity'),
        duration=symptom_data.get('duration'),
        extracted_by=symptom_data.get('extracted_by', 'ai_analysis'),
        confidence_score=symptom_data.get('confidence_score')
    )
    db.session.add(symptom)
    db.session.commit()
    return symptom

def add_health_metric(user_id, metric_type, value, unit, notes=None, source=None):
    """Add a new health metric measurement"""
    from database.models import HealthMetrics
    
    metric = HealthMetrics(
        user_id=user_id,
        metric_type=metric_type,
        value=value,
        unit=unit,
        notes=notes,
        source=source
    )
    db.session.add(metric)
    db.session.commit()
    return metric

def create_medical_report(user_id, report_type, content, format='pdf'):
    """Create a new medical report"""
    from database.models import MedicalReport
    
    report = MedicalReport(
        user_id=user_id,
        report_type=report_type,
        content=content,
        format=format
    )
    db.session.add(report)
    db.session.commit()
    return report

def get_emergency_contacts(user_id):
    """Get emergency contacts for a user"""
    from database.models import EmergencyContact
    return EmergencyContact.query.filter_by(user_id=user_id).all()

def add_emergency_contact(user_id, name, phone, relationship=None, email=None, is_primary=False):
    """Add a new emergency contact"""
    from database.models import EmergencyContact
    
    # If this is a primary contact, unset any existing primary contacts
    if is_primary:
        EmergencyContact.query.filter_by(user_id=user_id, is_primary=True)\
            .update({EmergencyContact.is_primary: False})
    
    contact = EmergencyContact(
        user_id=user_id,
        name=name,
        phone=phone,
        relationship=relationship,
        email=email,
        is_primary=is_primary
    )
    db.session.add(contact)
    db.session.commit()
    return contact
