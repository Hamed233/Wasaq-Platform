from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, session
from flask_login import login_required, current_user
from . import chatbot
from app.models.chat_message import ChatMessage
from app.ai.chatbot import WaqafChatbot
from app import db
import uuid
import os
from datetime import datetime

@chatbot.route('/')
def index():
    """Chatbot interface page"""
    # Create or get session ID
    if 'chat_session_id' not in session:
        session['chat_session_id'] = str(uuid.uuid4())
    
    # Get recent chat messages for this session
    chat_history = []
    if current_user.is_authenticated:
        # If user is logged in, get their chat history
        chat_history = ChatMessage.query.filter_by(
            user_id=current_user.id,
            session_id=session['chat_session_id']
        ).order_by(ChatMessage.created_at).all()
    else:
        # If user is not logged in, get session chat history
        chat_history = ChatMessage.query.filter_by(
            user_id=None,
            session_id=session['chat_session_id']
        ).order_by(ChatMessage.created_at).all()
    
    return render_template('chatbot/index.html', chat_history=chat_history)

@chatbot.route('/send', methods=['POST'])
def send_message():
    """Process user message and get chatbot response"""
    # Check if the request is JSON
    if request.is_json:
        data = request.get_json()
        message = data.get('message', '').strip()
    else:
        # Fall back to form data
        message = request.form.get('message', '').strip()
    
    if not message:
        return jsonify({
            'status': 'error',
            'message': 'Message cannot be empty'
        }), 400
    
    # Create or get session ID
    if 'chat_session_id' not in session:
        session['chat_session_id'] = str(uuid.uuid4())
    
    try:
        # Save user message to database
        user_message = ChatMessage(
            session_id=session['chat_session_id'],
            content=message,
            is_bot=False,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(user_message)
        
        # Process message with chatbot
        intents_file = os.path.join(current_app.root_path, 'ai', 'intents.json')
        bot = WaqafChatbot(intents_file=intents_file)
        
        # Get response from chatbot
        chat_response = bot.chat(message)
        
        # Save bot response to database
        bot_message = ChatMessage(
            session_id=session['chat_session_id'],
            content=chat_response['response'],
            is_bot=True,
            user_id=current_user.id if current_user.is_authenticated else None,
            intent=chat_response['intents'][0]['intent'] if chat_response['intents'] else None,
            confidence=float(chat_response['intents'][0]['probability']) if chat_response['intents'] else None
        )
        db.session.add(bot_message)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'response': bot_message.content,
            'suggestions': chat_response.get('suggestions', []),
            'user_message': {
                'id': user_message.id,
                'content': user_message.content,
                'timestamp': user_message.created_at.strftime('%Y-%m-%d %H:%M:%S')
            },
            'bot_message': {
                'id': bot_message.id,
                'content': bot_message.content,
                'timestamp': bot_message.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@chatbot.route('/history')
@login_required
def history():
    """View chat history (for logged-in users only)"""
    # Get all user's chat sessions
    sessions = db.session.query(ChatMessage.session_id, 
                               db.func.min(ChatMessage.created_at).label('start_time'),
                               db.func.count(ChatMessage.id).label('message_count'))\
                        .filter_by(user_id=current_user.id)\
                        .group_by(ChatMessage.session_id)\
                        .order_by(db.func.min(ChatMessage.created_at).desc())\
                        .all()
    
    return render_template('chatbot/history.html', sessions=sessions)

@chatbot.route('/history/<session_id>')
@login_required
def view_session(session_id):
    """View a specific chat session"""
    # Verify the session belongs to the current user
    session_exists = db.session.query(ChatMessage)\
                              .filter_by(user_id=current_user.id, session_id=session_id)\
                              .first()
    
    if not session_exists:
        flash('u0644u0627 u064au0645u0643u0646u0643 u0627u0644u0648u0635u0648u0644 u0625u0644u0649 u0647u0630u0647 u0627u0644u0645u062du0627u062fu062bu0629', 'danger')
        return redirect(url_for('chatbot.history'))
    
    # Get all messages in this session
    messages = ChatMessage.query.filter_by(
        user_id=current_user.id,
        session_id=session_id
    ).order_by(ChatMessage.created_at).all()
    
    return render_template('chatbot/view_session.html', messages=messages, session_id=session_id)

@chatbot.route('/clear', methods=['POST'])
def clear_session():
    """Clear the current chat session"""
    if 'chat_session_id' in session:
        session_id = session['chat_session_id']
        
        try:
            # Delete all messages in this session
            if current_user.is_authenticated:
                ChatMessage.query.filter_by(
                    user_id=current_user.id,
                    session_id=session_id
                ).delete()
            else:
                ChatMessage.query.filter_by(
                    user_id=None,
                    session_id=session_id
                ).delete()
            
            db.session.commit()
            
            # Generate a new session ID
            session['chat_session_id'] = str(uuid.uuid4())
            
            return jsonify({
                'status': 'success',
                'message': 'Chat session cleared'
            })
        
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    return jsonify({
        'status': 'error',
        'message': 'No active chat session'
    }), 400
