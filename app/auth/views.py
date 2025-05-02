from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, ResetPasswordRequestForm, ResetPasswordForm, EditProfileForm
from app.models.user import User
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
import re

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user is not None and user.verify_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            user.update_last_login()
            next_page = request.args.get('next')
            if next_page is None or not next_page.startswith('/'):
                next_page = url_for('dashboard.index')
            return redirect(next_page)
        
        flash('البريد الإلكتروني أو كلمة المرور غير صحيحة', 'danger')
    
    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    """User logout route"""
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('main.index'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Create new user
        new_user = User(
            email=form.email.data,
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            password=form.password.data,
            role='user'
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('تم التسجيل بنجاح! يمكنك الآن تسجيل الدخول', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@auth.route('/profile')
@login_required
def profile():
    """User profile route"""
    return render_template('auth/profile.html')

@auth.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile route"""
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        
        # Check if email is being changed
        new_email = form.email.data
        if new_email != current_user.email:
            # Validate email format
            if not re.match(r'^[\w.-]+@[\w.-]+\.[a-zA-Z]{2,}$', new_email):
                flash('البريد الإلكتروني غير صالح', 'danger')
                return render_template('auth/edit_profile.html', form=form)
            
            # Check if email already exists
            if User.query.filter_by(email=new_email).first():
                flash('البريد الإلكتروني مستخدم بالفعل', 'danger')
                return render_template('auth/edit_profile.html', form=form)
            
            current_user.email = new_email
        
        # Check if password is being changed
        new_password = form.new_password.data
        if new_password:
            current_password = form.current_password.data
            password_confirm = form.password_confirm.data
            
            # Verify current password
            if not current_user.verify_password(current_password):
                flash('كلمة المرور الحالية غير صحيحة', 'danger')
                return render_template('auth/edit_profile.html', form=form)
            
            # Validate password length
            if len(new_password) < 8:
                flash('كلمة المرور الجديدة يجب أن تكون 8 أحرف على الأقل', 'danger')
                return render_template('auth/edit_profile.html', form=form)
            
            # Validate password match
            if new_password != password_confirm:
                flash('كلمات المرور الجديدة غير متطابقة', 'danger')
                return render_template('auth/edit_profile.html', form=form)
            
            current_user.password = new_password
        
        db.session.commit()
        flash('تم تحديث الملف الشخصي بنجاح', 'success')
        return redirect(url_for('auth.profile'))
    
    form.first_name.data = current_user.first_name
    form.last_name.data = current_user.last_name
    form.email.data = current_user.email
    return render_template('auth/edit_profile.html', form=form)

@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    """Request password reset route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        
        if user:
            # In a real application, send a password reset email here
            # For now, we'll just flash a message
            flash('تم إرسال تعليمات إعادة تعيين كلمة المرور إلى بريدك الإلكتروني', 'info')
        else:
            # Don't reveal that the user doesn't exist
            flash('تم إرسال تعليمات إعادة تعيين كلمة المرور إلى بريدك الإلكتروني', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password_request.html', form=form)
