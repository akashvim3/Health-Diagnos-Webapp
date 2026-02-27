"""
Dashboard Routes
Handles user dashboard with health data, chat history, and reports
"""
from flask import Blueprint, render_template, send_file, jsonify, request, redirect, url_for, flash
from flask_login import login_required, current_user
from database.models import db, ChatSession, ChatMessage, HealthRecord, HealthMetrics, SymptomRecord
from database.utils import get_user_health_records, update_health_record, get_emergency_contacts
from utils.pdf_generator import generate_pdf
from datetime import datetime, timedelta
import json

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def dashboard():
    """Main dashboard page with health overview"""
    # Get user's chat sessions
    chat_sessions = ChatSession.query.filter_by(
        user_id=current_user.id
    ).order_by(
        ChatSession.started_at.desc()
    ).limit(10).all()
    
    # Get health records
    health_record = get_user_health_records(current_user.id)
    
    # Get recent symptoms
    recent_symptoms = SymptomRecord.query.join(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(
        SymptomRecord.recorded_at.desc()
    ).limit(20).all()
    
    # Get health metrics
    health_metrics = HealthMetrics.query.filter_by(
        user_id=current_user.id
    ).order_by(
        HealthMetrics.recorded_at.desc()
    ).limit(10).all()
    
    # Get emergency contacts
    emergency_contacts = get_emergency_contacts(current_user.id)
    
    # Calculate statistics
    stats = {
        'total_sessions': ChatSession.query.filter_by(user_id=current_user.id).count(),
        'total_messages': ChatMessage.query.join(ChatSession).filter(
            ChatSession.user_id == current_user.id
        ).count(),
        'unique_symptoms': len(set(s.symptom_name for s in recent_symptoms)),
        'recent_activity': chat_sessions[0].started_at if chat_sessions else None
    }
    
    return render_template('dashboard.html',
                         chat_sessions=chat_sessions,
                         health_record=health_record,
                         recent_symptoms=recent_symptoms,
                         health_metrics=health_metrics,
                         emergency_contacts=emergency_contacts,
                         stats=stats)


@dashboard_bp.route('/history')
@login_required
def chat_history():
    """Chat history page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    sessions = ChatSession.query.filter_by(
        user_id=current_user.id
    ).order_by(
        ChatSession.started_at.desc()
    ).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('dashboard/history.html', sessions=sessions)


@dashboard_bp.route('/session/<int:session_id>')
@login_required
def session_detail(session_id):
    """View a specific chat session"""
    session = ChatSession.query.get_or_404(session_id)
    
    # Ensure user owns this session
    if session.user_id != current_user.id:
        flash('You do not have permission to view this session', 'error')
        return redirect(url_for('dashboard.chat_history'))
    
    messages = ChatMessage.query.filter_by(
        session_id=session_id
    ).order_by(ChatMessage.timestamp).all()
    
    symptoms = SymptomRecord.query.filter_by(
        session_id=session_id
    ).order_by(SymptomRecord.recorded_at).all()
    
    return render_template('dashboard/session.html', 
                         session=session, 
                         messages=messages,
                         symptoms=symptoms)


@dashboard_bp.route('/health-records', methods=['GET', 'POST'])
@login_required
def health_records():
    """Manage health records"""
    if request.method == 'POST':
        data = request.get_json() or request.form.to_dict()
        
        # Update health record
        record_data = {
            'conditions': data.get('conditions', []),
            'medications': data.get('medications', []),
            'allergies': data.get('allergies', []),
            'chronic_conditions': data.get('chronic_conditions', [])
        }
        
        update_health_record(current_user.id, record_data)
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Health records updated successfully'})
        
        flash('Health records updated successfully', 'success')
        return redirect(url_for('dashboard.health_records'))
    
    health_record = get_user_health_records(current_user.id)
    return render_template('dashboard/health_records.html', health_record=health_record)


@dashboard_bp.route('/health-metrics', methods=['GET', 'POST'])
@login_required
def health_metrics():
    """Track and display health metrics"""
    if request.method == 'POST':
        data = request.get_json() or request.form.to_dict()
        
        metric_type = data.get('metric_type')
        value = data.get('value', type=float)
        unit = data.get('unit')
        
        if not all([metric_type, value, unit]):
            if request.is_json:
                return jsonify({'success': False, 'error': 'Missing required fields'}), 400
            flash('Missing required fields', 'error')
            return redirect(url_for('dashboard.health_metrics'))
        
        # Add health metric
        from database.utils import add_health_metric
        add_health_metric(
            user_id=current_user.id,
            metric_type=metric_type,
            value=value,
            unit=unit,
            notes=data.get('notes'),
            source='user_input'
        )
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Metric added successfully'})
        
        flash('Health metric added successfully', 'success')
        return redirect(url_for('dashboard.health_metrics'))
    
    # Get all metrics for the user
    metrics = HealthMetrics.query.filter_by(
        user_id=current_user.id
    ).order_by(
        HealthMetrics.recorded_at.desc()
    ).limit(50).all()
    
    # Group by metric type
    metrics_by_type = {}
    for metric in metrics:
        if metric.metric_type not in metrics_by_type:
            metrics_by_type[metric.metric_type] = []
        metrics_by_type[metric.metric_type].append(metric)
    
    return render_template('dashboard/health_metrics.html', 
                         metrics=metrics,
                         metrics_by_type=metrics_by_type)


@dashboard_bp.route('/emergency-contacts', methods=['GET', 'POST'])
@login_required
def emergency_contacts_page():
    """Manage emergency contacts"""
    if request.method == 'POST':
        data = request.get_json() or request.form.to_dict()
        
        name = data.get('name')
        phone = data.get('phone')
        relationship = data.get('relationship')
        email = data.get('email')
        is_primary = data.get('is_primary', False)
        
        if not name or not phone:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Name and phone are required'}), 400
            flash('Name and phone are required', 'error')
            return redirect(url_for('dashboard.emergency_contacts_page'))
        
        from database.utils import add_emergency_contact
        add_emergency_contact(
            user_id=current_user.id,
            name=name,
            phone=phone,
            relationship=relationship,
            email=email,
            is_primary=is_primary
        )
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Emergency contact added successfully'})
        
        flash('Emergency contact added successfully', 'success')
        return redirect(url_for('dashboard.emergency_contacts_page'))
    
    contacts = get_emergency_contacts(current_user.id)
    return render_template('dashboard/emergency_contacts.html', contacts=contacts)


@dashboard_bp.route('/download-report')
@login_required
def download_report():
    """Generate and download PDF report"""
    try:
        pdf_path = generate_pdf(current_user.id)
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f'health_report_{current_user.username}_{datetime.now().strftime("%Y%m%d")}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('dashboard.dashboard'))


@dashboard_bp.route('/api/stats')
@login_required
def get_stats():
    """API endpoint for dashboard statistics"""
    # Get statistics
    total_sessions = ChatSession.query.filter_by(user_id=current_user.id).count()
    total_messages = ChatMessage.query.join(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).count()
    
    # Get symptoms count by type
    symptoms = SymptomRecord.query.join(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).all()
    
    symptom_counts = {}
    for symptom in symptoms:
        symptom_counts[symptom.symptom_name] = symptom_counts.get(symptom.symptom_name, 0) + 1
    
    # Get activity over time (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_sessions = ChatSession.query.filter(
        ChatSession.user_id == current_user.id,
        ChatSession.started_at >= thirty_days_ago
    ).all()
    
    activity_by_day = {}
    for session in recent_sessions:
        day = session.started_at.strftime('%Y-%m-%d')
        activity_by_day[day] = activity_by_day.get(day, 0) + 1
    
    return jsonify({
        'total_sessions': total_sessions,
        'total_messages': total_messages,
        'symptom_counts': symptom_counts,
        'activity_by_day': activity_by_day
    })


@dashboard_bp.route('/delete-session/<int:session_id>', methods=['POST'])
@login_required
def delete_session(session_id):
    """Delete a chat session"""
    session = ChatSession.query.get_or_404(session_id)
    
    if session.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        # Delete messages first
        ChatMessage.query.filter_by(session_id=session_id).delete()
        SymptomRecord.query.filter_by(session_id=session_id).delete()
        
        # Delete session
        db.session.delete(session)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Session deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
