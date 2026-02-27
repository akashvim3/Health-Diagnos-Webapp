"""
Authentication Routes
Handles user registration, login, logout, and profile management
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from database.models import db, User
from database.utils import create_user
import re

auth_bp = Blueprint('auth', __name__)


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """
    Validate password strength
    Returns (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page and handler"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    if request.method == 'POST':
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        remember = data.get('remember', False)
        
        # Validate input
        if not email or not password:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Email and password are required'}), 400
            flash('Email and password are required', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user is None:
            user = User.query.filter_by(username=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            
            # Update last login
            from datetime import datetime
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard.dashboard')
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': next_page})
            
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page)
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page and handler"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        
        # Validate input
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long')
        
        if not validate_email(email):
            errors.append('Please enter a valid email address')
        
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            errors.append(error_msg)
        
        if password != confirm_password:
            errors.append('Passwords do not match')
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered')
        
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken')
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')
        
        # Create new user
        try:
            user = User(email=email, username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please log in.', 'success')
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': url_for('auth.login')})
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'errors': ['Registration failed. Please try again.']}), 500
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout handler"""
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('index'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page and update handler"""
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        # Update user profile
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        
        errors = []
        
        # Check if username is taken
        if username != current_user.username:
            if User.query.filter_by(username=username).first():
                errors.append('Username already taken')
            else:
                current_user.username = username
        
        # Check if email is taken
        if email != current_user.email:
            if User.query.filter_by(email=email).first():
                errors.append('Email already in use')
            else:
                current_user.email = email
        
        # Update password if provided
        new_password = data.get('new_password', '')
        current_password = data.get('current_password', '')
        
        if new_password:
            if not current_user.check_password(current_password):
                errors.append('Current password is incorrect')
            else:
                is_valid, error_msg = validate_password(new_password)
                if not is_valid:
                    errors.append(error_msg)
                else:
                    current_user.set_password(new_password)
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            for error in errors:
                flash(error, 'error')
        else:
            try:
                db.session.commit()
                flash('Profile updated successfully', 'success')
                if request.is_json:
                    return jsonify({'success': True})
            except Exception:
                db.session.rollback()
                flash('Failed to update profile', 'error')
    
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/api/check-email')
def check_email():
    """API endpoint to check if email is available"""
    email = request.args.get('email', '').strip().lower()
    
    if not validate_email(email):
        return jsonify({'valid': False, 'message': 'Invalid email format'})
    
    exists = User.query.filter_by(email=email).first() is not None
    return jsonify({
        'valid': not exists,
        'message': 'Email already registered' if exists else 'Email available'
    })


@auth_bp.route('/api/check-username')
def check_username():
    """API endpoint to check if username is available"""
    username = request.args.get('username', '').strip()
    
    if len(username) < 3:
        return jsonify({'valid': False, 'message': 'Username must be at least 3 characters'})
    
    exists = User.query.filter_by(username=username).first() is not None
    return jsonify({
        'valid': not exists,
        'message': 'Username already taken' if exists else 'Username available'
    })
