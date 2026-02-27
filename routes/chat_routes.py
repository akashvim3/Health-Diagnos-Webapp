"""
Chat Routes
Handles chat functionality with symptom extraction and AI responses
"""
from flask import Blueprint, jsonify, request, render_template, current_app
from flask_login import login_required, current_user
from models.symptom_extractor import SymptomExtractor
from models.diagnosis_engine import DiagnosisEngine
from database.models import db, ChatSession, ChatMessage, SymptomRecord
from database.utils import create_chat_session, add_chat_message
from utils.preprocessing import preprocess_text, extract_temporal_info, extract_severity_info
import openai
import logging

# Set up logging
logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)

# Initialize models (lazy loading)
_symptom_extractor = None
_diagnosis_engine = None


def get_symptom_extractor():
    """Get or initialize symptom extractor"""
    global _symptom_extractor
    if _symptom_extractor is None:
        try:
            _symptom_extractor = SymptomExtractor()
        except Exception as e:
            logger.warning(f"Could not load BioBERT model, using fallback: {e}")
            _symptom_extractor = None
    return _symptom_extractor


def get_diagnosis_engine():
    """Get or initialize diagnosis engine"""
    global _diagnosis_engine
    if _diagnosis_engine is None:
        try:
            _diagnosis_engine = DiagnosisEngine()
            _diagnosis_engine.load_model()
        except Exception as e:
            logger.warning(f"Could not load diagnosis model, using fallback: {e}")
            _diagnosis_engine = None
    return _diagnosis_engine


@chat_bp.route('/')
def chat_page():
    """Main chat page"""
    # Get user's recent chat sessions
    recent_sessions = []
    if current_user.is_authenticated:
        recent_sessions = ChatSession.query.filter_by(
            user_id=current_user.id
        ).order_by(
            ChatSession.started_at.desc()
        ).limit(5).all()
    
    return render_template('chat.html', recent_sessions=recent_sessions)


@chat_bp.route('/api/chat', methods=['POST'])
def process_message():
    """
    Process user message and generate AI response
    Expects JSON: {"message": "user message", "session_id": optional}
    Returns JSON: {"response": "AI response", "symptoms": [], "conditions": []}
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({
                'success': False,
                'error': 'Message cannot be empty'
            }), 400
        
        # Check for emergency keywords
        emergency_keywords = ['emergency', 'severe pain', 'unconscious', 
                             'difficulty breathing', 'chest pain', 'stroke']
        
        is_emergency = any(keyword in user_message.lower() for keyword in emergency_keywords)
        
        # Preprocess the message
        preprocessed_text = preprocess_text(user_message)
        
        # Extract symptoms
        symptoms = extract_symptoms(user_message)
        
        # Get possible conditions
        conditions = predict_conditions(symptoms)
        
        # Generate AI response
        response = generate_response(user_message, symptoms, conditions)
        
        # Store message in database if user is authenticated
        session_id = data.get('session_id')
        
        if current_user.is_authenticated:
            # Create or get chat session
            if session_id:
                chat_session = ChatSession.query.get(session_id)
                if not chat_session or chat_session.user_id != current_user.id:
                    chat_session = create_chat_session(current_user.id)
            else:
                chat_session = create_chat_session(current_user.id)
            
            # Store user message
            user_msg = add_chat_message(
                session_id=chat_session.id,
                message_type='user',
                content=user_message,
                symptoms=symptoms,
                conditions=conditions
            )
            
            # Store AI response
            ai_msg = add_chat_message(
                session_id=chat_session.id,
                message_type='ai',
                content=response,
                symptoms=symptoms,
                conditions=conditions
            )
            
            # Store symptom records
            for symptom in symptoms:
                symptom_record = SymptomRecord(
                    session_id=chat_session.id,
                    symptom_name=symptom.get('name', ''),
                    severity=symptom.get('severity'),
                    duration=symptom.get('duration'),
                    extracted_by='ai_analysis',
                    confidence_score=symptom.get('confidence', 0.8)
                )
                db.session.add(symptom_record)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'response': response,
                'symptoms': symptoms,
                'conditions': conditions,
                'session_id': chat_session.id,
                'is_emergency': is_emergency
            })
        
        return jsonify({
            'success': True,
            'response': response,
            'symptoms': symptoms,
            'conditions': conditions,
            'is_emergency': is_emergency
        })
        
    except openai.error.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        return jsonify({
            'success': False,
            'error': 'AI service temporarily unavailable. Please try again.',
            'fallback_response': get_fallback_response(user_message)
        }), 503
        
    except openai.error.RateLimitError:
        logger.error("OpenAI rate limit exceeded")
        return jsonify({
            'success': False,
            'error': 'Service is busy. Please try again in a moment.',
            'fallback_response': get_fallback_response(user_message)
        }), 429
        
    except Exception as e:
        logger.exception(f"Error processing message: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.',
            'fallback_response': get_fallback_response(user_message)
        }), 500


@chat_bp.route('/api/symptoms', methods=['GET'])
def get_symptoms():
    """Get list of common symptoms"""
    common_symptoms = [
        "fever", "cough", "headache", "fatigue", "nausea",
        "sore throat", "runny nose", "body aches", "chills",
        "shortness of breath", "chest pain", "abdominal pain",
        "dizziness", "rash", "vomiting", "diarrhea"
    ]
    return jsonify({'symptoms': common_symptoms})


@chat_bp.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    """Get user's chat sessions"""
    sessions = ChatSession.query.filter_by(
        user_id=current_user.id
    ).order_by(
        ChatSession.started_at.desc()
    ).all()
    
    return jsonify({
        'sessions': [{
            'id': s.id,
            'started_at': s.started_at.isoformat(),
            'ended_at': s.ended_at.isoformat() if s.ended_at else None,
            'message_count': len(s.messages)
        } for s in sessions]
    })


@chat_bp.route('/api/sessions/<int:session_id>', methods=['GET'])
@login_required
def get_session(session_id):
    """Get a specific chat session with messages"""
    session = ChatSession.query.get_or_404(session_id)
    
    if session.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    messages = ChatMessage.query.filter_by(
        session_id=session_id
    ).order_by(ChatMessage.timestamp).all()
    
    return jsonify({
        'session': {
            'id': session.id,
            'started_at': session.started_at.isoformat(),
            'ended_at': session.ended_at.isoformat() if session.ended_at else None
        },
        'messages': [{
            'id': m.id,
            'type': m.message_type,
            'content': m.content,
            'timestamp': m.timestamp.isoformat(),
            'detected_symptoms': m.detected_symptoms,
            'suggested_conditions': m.suggested_conditions,
            'confidence_score': m.confidence_score
        } for m in messages]
    })


def extract_symptoms(text):
    """Extract symptoms from user text"""
    # Try using the ML model first
    extractor = get_symptom_extractor()
    
    if extractor:
        try:
            symptoms = extractor.extract_symptoms(text)
            return symptoms
        except Exception as e:
            logger.warning(f"Symptom extraction failed: {e}")
    
    # Fallback to keyword-based extraction
    return keyword_based_symptom_extraction(text)


def keyword_based_symptom_extraction(text):
    """Fallback symptom extraction using keyword matching"""
    text = text.lower()
    
    symptom_keywords = {
        'fever': {'name': 'fever', 'keywords': ['fever', 'high temperature', 'hot']},
        'cough': {'name': 'cough', 'keywords': ['cough', 'coughing']},
        'headache': {'name': 'headache', 'keywords': ['headache', 'head pain', 'head ache']},
        'fatigue': {'name': 'fatigue', 'keywords': ['tired', 'fatigue', 'exhausted', 'weak']},
        'nausea': {'name': 'nausea', 'keywords': ['nausea', 'nauseous', 'sick']},
        'sore throat': {'name': 'sore throat', 'keywords': ['sore throat', 'throat pain']},
        'runny nose': {'name': 'runny nose', 'keywords': ['runny nose', 'nasal discharge']},
        'body aches': {'name': 'body aches', 'keywords': ['body ache', 'body pain', 'muscle pain']},
        'shortness of breath': {'name': 'shortness of breath', 'keywords': ['shortness of breath', 'difficulty breathing', 'breathlessness']},
        'chest pain': {'name': 'chest pain', 'keywords': ['chest pain', 'chest discomfort']},
        'abdominal pain': {'name': 'abdominal pain', 'keywords': ['stomach pain', 'abdominal pain', 'belly pain']},
        'dizziness': {'name': 'dizziness', 'keywords': ['dizziness', 'dizzy', 'lightheaded']},
        'vomiting': {'name': 'vomiting', 'keywords': ['vomiting', 'vomit', 'throwing up']},
        'diarrhea': {'name': 'diarrhea', 'keywords': ['diarrhea', 'loose stool']}
    }
    
    detected_symptoms = []
    
    for symptom_key, symptom_data in symptom_keywords.items():
        for keyword in symptom_data['keywords']:
            if keyword in text:
                # Extract temporal info
                duration = extract_temporal_info(text)
                severity = extract_severity_info(text)
                
                detected_symptoms.append({
                    'name': symptom_data['name'],
                    'duration': duration,
                    'severity': severity,
                    'confidence': 0.7
                })
                break
    
    return detected_symptoms


def predict_conditions(symptoms):
    """Predict possible conditions based on symptoms"""
    engine = get_diagnosis_engine()
    
    if engine:
        try:
            conditions = engine.predict_conditions(symptoms)
            return conditions
        except Exception as e:
            logger.warning(f"Condition prediction failed: {e}")
    
    # Fallback to rule-based prediction
    return rule_based_prediction(symptoms)


def rule_based_prediction(symptoms):
    """Simple rule-based condition prediction"""
    symptom_names = [s.get('name', '').lower() for s in symptoms]
    
    conditions = []
    
    # Common cold pattern
    if 'runny nose' in symptom_names or 'sore throat' in symptom_names:
        conditions.append({'name': 'Common Cold', 'confidence': 0.7})
    
    # Flu pattern
    if 'fever' in symptom_names and ('body aches' in symptom_names or 'fatigue' in symptom_names):
        conditions.append({'name': 'Influenza (Flu)', 'confidence': 0.75})
    
    # COVID-19 pattern
    if 'fever' in symptom_names and 'cough' in symptom_names and 'shortness of breath' in symptom_names:
        conditions.append({'name': 'COVID-19', 'confidence': 0.6})
    
    # Return top 3 conditions
    return conditions[:3] if conditions else [{'name': 'General Discomfort', 'confidence': 0.5}]


def generate_response(user_message, symptoms, conditions):
    """Generate AI response using OpenAI API"""
    
    # Construct symptom list for prompt
    symptom_list = [s.get('name', 'Unknown') for s in symptoms]
    condition_list = [c.get('name', 'Unknown') for c in conditions]
    
    # Build prompt
    prompt = f"""You are a professional, empathetic healthcare assistant. 

User's concern: {user_message}

Detected symptoms: {', '.join(symptom_list) if symptom_list else 'None specified'}

Possible conditions to consider: {', '.join(condition_list) if condition_list else 'Unable to determine'}

Generate a helpful, empathetic response that:
1. Acknowledges the user's symptoms or concern
2. Provides general, non-specific health information
3. Suggests when to seek professional medical attention
4. ALWAYS includes a clear medical disclaimer
5. Recommends next steps (rest, hydration, over-the-counter remedies if appropriate)

Remember: You are NOT a doctor and cannot provide specific medical diagnoses. Always encourage users to consult with healthcare professionals for proper evaluation.

Keep the response concise but informative (150-300 words)."""
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful healthcare assistant. Provide general health information only. Always include disclaimers. Never provide specific medical diagnoses. Encourage users to seek professional medical advice."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message['content']
        
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return get_fallback_response(user_message)


def get_fallback_response(user_message):
    """Generate a fallback response when AI is unavailable"""
    return """Thank you for sharing your symptoms with me. 

Based on your concern, I recommend:

1. **Rest and Hydration**: Make sure to drink plenty of fluids and get adequate rest.

2. **Over-the-Counter Relief**: For mild symptoms, over-the-counter medications may help (consult a pharmacist for recommendations).

3. **Monitor Your Symptoms**: Keep track of your symptoms and their severity.

4. **Seek Medical Attention**: Please consult with a healthcare professional if:
   - Your symptoms worsen or don't improve within a few days
   - You develop high fever (above 103°F/39.4°C)
   - You experience severe pain or difficulty breathing
   - You have underlying health conditions

**IMPORTANT DISCLAIMER**: This is general information only and is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition."""
