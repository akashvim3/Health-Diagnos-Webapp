from flask import Blueprint, jsonify, request, render_template
from models.symptom_extractor import SymptomExtractor
from models.diagnosis_engine import DiagnosisEngine
import openai

chat_bp = Blueprint('chat', __name__)

# Initialize models
symptom_extractor = SymptomExtractor()
diagnosis_engine = DiagnosisEngine()

@chat_bp.route('/chat')
def chat_page():
    return render_template('chat.html')

@chat_bp.route('/api/chat', methods=['POST'])
def process_message():
    data = request.json
    user_message = data.get('message', '')
    
    # Extract symptoms from user message
    symptoms = symptom_extractor.extract_symptoms(user_message)
    
    # Get possible conditions
    conditions = diagnosis_engine.predict_conditions(symptoms)
    
    # Generate response using GPT
    response = generate_response(user_message, symptoms, conditions)
    
    return jsonify({
        'response': response,
        'symptoms': symptoms,
        'conditions': conditions
    })

def generate_response(user_message, symptoms, conditions):
    # Construct prompt for GPT
    prompt = f"""
    User Message: {user_message}
    Extracted Symptoms: {', '.join(symptoms)}
    Possible Conditions: {conditions}
    
    Generate a helpful and empathetic response that:
    1. Acknowledges the symptoms
    2. Provides general advice
    3. Suggests when to seek medical attention
    4. Includes a medical disclaimer
    """
    
    # Call OpenAI API
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful healthcare assistant. Always include disclaimers and encourage seeking professional medical advice."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message['content']
