from flask import Blueprint, render_template
from flask_login import login_required, current_user
from utils.pdf_generator import generate_pdf

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    # Get user's chat history and health data
    chat_history = get_chat_history(current_user.id)
    health_data = get_health_data(current_user.id)
    
    return render_template('dashboard.html',
                         chat_history=chat_history,
                         health_data=health_data)

@dashboard_bp.route('/download-report')
@login_required
def download_report():
    # Generate PDF report
    pdf_path = generate_pdf(current_user.id)
    return send_file(pdf_path, as_attachment=True)

def get_chat_history(user_id):
    # Implement chat history retrieval
    return []

def get_health_data(user_id):
    # Implement health data retrieval
    return {
        'symptoms': [],
        'conditions': [],
        'recommendations': []
    }
