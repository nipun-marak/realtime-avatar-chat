from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from flask_session import Session
import json
import datetime
import os
from database import (
    init_db, get_or_create_user, update_user, log_conversation, 
    get_recent_conversations, retrieve_relevant_memories, view_tasks
)
from ai_core import get_ai_response
from voice_utils import generate_audio_base64, generate_audio_with_visemes
from forms import LoginForm, ChatForm, VoiceToggleForm, FullscreenToggleForm, AvatarStateForm
from config import DEBUG, HOST, PORT

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure session to avoid cookie size limits
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'mindful_companion:'

CORS(app)

# Initialize Flask-Session
Session(app)

socketio = SocketIO(app, cors_allowed_origins="*")

# Global user storage (in production, use proper session management)
current_user = None

@app.route('/')
def index():
    """Main application page - redirects to login or chat based on session."""
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and form handling."""
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data.strip()
        
        # Initialize database
        init_db()
        
        # Get or create user
        global current_user
        current_user = get_or_create_user(username)
        
        # Store minimal user data in session to avoid cookie size limits
        session['user_id'] = current_user['id']
        session['username'] = username
        session['avatar_state'] = 'idle'
        session['voice_enabled'] = True
        session['fullscreen'] = False
        
        # Generate smart greeting
        greeting_message = generate_smart_greeting(current_user)
        
        # Update last seen
        update_user(current_user['id'], "last_seen", datetime.datetime.now().isoformat())
        
        # Generate audio for greeting
        audio_b64 = generate_audio_base64(greeting_message)
        
        # Store minimal session data to avoid cookie size limits
        # Don't store large data like audio in session
        
        flash(f'Welcome back, {username}!', 'success')
        return redirect(url_for('chat'))
    
    return render_template('login.html', form=form)

@app.route('/chat')
def chat():
    """Main chat interface."""
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))
    
    # Get current user
    global current_user
    if not current_user or current_user['id'] != session['user_id']:
        try:
            current_user = get_or_create_user(session['username'])
        except Exception as e:
            print(f"Error getting/creating user: {e}")
            flash('Error accessing user data. Please try logging in again.', 'error')
            return redirect(url_for('login'))
    
    # Initialize database if needed
    init_db()
    
    # Get recent messages
    messages = []
    try:
        recent_conversations = get_recent_conversations(current_user['id'], limit=10)
        for conv in recent_conversations:
            messages.append({
                'text': conv['message'],
                'sender': conv['role']
            })
    except Exception as e:
        print(f"Error getting recent conversations: {e}")
        messages = []
    
    # Check if this is a new session (no recent messages) and add greeting
    if not messages:
        try:
            greeting_message = generate_smart_greeting(current_user)
            messages.append({
                'text': greeting_message,
                'sender': 'bot'
            })
        except Exception as e:
            print(f"Error generating greeting: {e}")
            messages.append({
                'text': f"Hello, {current_user['username']}! How can I help you today?",
                'sender': 'bot'
            })
    
    return render_template('chat.html', 
                         current_user=current_user, 
                         messages=messages,
                         form=ChatForm())

@app.route('/api/start_session', methods=['POST'])
def start_session():
    """API endpoint for starting a session (legacy support)."""
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    # Initialize database
    init_db()
    
    # Get or create user
    global current_user
    current_user = get_or_create_user(username)
    
    # Store user in session
    session['user_id'] = current_user['id']
    session['username'] = username
    session['avatar_state'] = 'idle'
    session['voice_enabled'] = True
    session['fullscreen'] = False
    
    # Generate smart greeting
    greeting_message = generate_smart_greeting(current_user)
    
    # Update last seen
    update_user(current_user['id'], "last_seen", datetime.datetime.now().isoformat())
    
    # Generate audio for greeting with viseme data
    audio_data = generate_audio_with_visemes(greeting_message)
    
    if audio_data:
        return jsonify({
            'message': greeting_message,
            'audio': audio_data['audio'],
            'viseme_frames': audio_data['viseme_frames'],
            'estimated_duration': audio_data['estimated_duration'],
            'user': current_user
        })
    else:
        # Fallback to basic audio generation
        audio_b64 = generate_audio_base64(greeting_message)
        return jsonify({
            'message': greeting_message,
            'audio': audio_b64,
            'user': current_user
        })

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handle chat messages."""
    global current_user
    
    if 'user_id' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    if not current_user or current_user['id'] != session['user_id']:
        current_user = get_or_create_user(session['username'])
    
    data = request.get_json()
    user_input = data.get('message', '').strip()
    
    if not user_input:
        return jsonify({'error': 'Message is required'}), 400
    
    # Handle commands
    if user_input.lower().startswith('/'):
        response_text = handle_command(user_input)
    else:
        # Regular conversation
        conversation_history = get_recent_conversations(current_user['id'], limit=30)
        memories = retrieve_relevant_memories(current_user['id'], user_input, top_k=7)
        ai_output = get_ai_response(user_input, current_user, conversation_history, memories)
        
        response_text = ai_output.get('response', "I'm not sure how to reply.")
        
        # Log conversation
        log_conversation(current_user['id'], 'user', user_input)
        log_conversation(current_user['id'], 'model', response_text)
        
        # Update user data
        new_summary = ai_output.get('updated_summary', current_user['personality_summary'])
        new_behavioral_notes = ai_output.get('updated_behavioral_notes', current_user.get('behavioral_notes'))
        
        if new_summary != current_user['personality_summary']:
            update_user(current_user['id'], "personality_summary", new_summary)
            current_user['personality_summary'] = new_summary
        
        if new_behavioral_notes != current_user.get('behavioral_notes'):
            update_user(current_user['id'], "behavioral_notes", new_behavioral_notes)
            current_user['behavioral_notes'] = new_behavioral_notes
    
    # Generate audio response with viseme data
    audio_data = generate_audio_with_visemes(response_text)
    
    if audio_data:
        return jsonify({
            'message': response_text,
            'audio': audio_data['audio'],
            'viseme_frames': audio_data['viseme_frames'],
            'estimated_duration': audio_data['estimated_duration']
        })
    else:
        # Fallback to basic audio generation
        audio_b64 = generate_audio_base64(response_text)
        return jsonify({
            'message': response_text,
            'audio': audio_b64
        })

@app.route('/send_message', methods=['POST'])
def send_message():
    """Handle chat message form submission."""
    if 'user_id' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))
    
    form = ChatForm()
    if form.validate_on_submit():
        message = form.message.data.strip()
        
        # Process the message (same logic as API endpoint)
        global current_user
        if not current_user or current_user['id'] != session['user_id']:
            current_user = get_or_create_user(session['username'])
        
        conversation_history = get_recent_conversations(current_user['id'], limit=30)
        memories = retrieve_relevant_memories(current_user['id'], message, top_k=7)
        ai_output = get_ai_response(message, current_user, conversation_history, memories)
        
        response_text = ai_output.get('response', "I'm not sure how to reply.")
        
        # Log conversation
        log_conversation(current_user['id'], 'user', message)
        log_conversation(current_user['id'], 'model', response_text)
        
        # Update user data
        new_summary = ai_output.get('updated_summary', current_user['personality_summary'])
        new_behavioral_notes = ai_output.get('updated_behavioral_notes', current_user.get('behavioral_notes'))
        
        if new_summary != current_user['personality_summary']:
            update_user(current_user['id'], "personality_summary", new_summary)
            current_user['personality_summary'] = new_summary
        
        if new_behavioral_notes != current_user.get('behavioral_notes'):
            update_user(current_user['id'], "behavioral_notes", new_behavioral_notes)
            current_user['behavioral_notes'] = new_behavioral_notes
        
        # Emit socket event for real-time updates
        socketio.emit('message_received', {
            'message': response_text,
            'sender': 'bot'
        })
    
    return redirect(url_for('chat'))

# Avatar state management
@app.route('/api/avatar_state', methods=['POST'])
def set_avatar_state():
    """Handle avatar state changes."""
    global current_user
    
    if 'user_id' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    if not current_user or current_user['id'] != session['user_id']:
        current_user = get_or_create_user(session['username'])
    
    data = request.get_json()
    state = data.get('state', 'idle')
    
    # Validate state
    valid_states = ['idle', 'listening', 'thinking', 'speaking']
    if state not in valid_states:
        return jsonify({'error': 'Invalid avatar state'}), 400
    
    # Store avatar state in session
    session['avatar_state'] = state
    
    return jsonify({
        'state': state,
        'status_label': state.capitalize(),
        'message': f'Avatar state changed to {state}'
    })

@app.route('/api/avatar_state', methods=['GET'])
def get_avatar_state():
    """Get current avatar state."""
    current_state = session.get('avatar_state', 'idle')
    return jsonify({
        'state': current_state,
        'status_label': current_state.capitalize()
    })

@app.route('/api/toggle_voice', methods=['POST'])
def toggle_voice():
    """Toggle voice output on/off."""
    if 'user_id' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    data = request.get_json()
    is_enabled = data.get('enabled', True)
    
    session['voice_enabled'] = is_enabled
    
    return jsonify({
        'voice_enabled': is_enabled,
        'icon': '🔊' if is_enabled else '🔇',
        'message': f'Voice output {"enabled" if is_enabled else "disabled"}'
    })

@app.route('/api/audio/play', methods=['POST'])
def play_audio():
    """Handle audio playback requests."""
    global current_user
    
    if 'user_id' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    if not current_user or current_user['id'] != session['user_id']:
        current_user = get_or_create_user(session['username'])
    
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'Text is required for audio generation'}), 400
    
    # Generate audio with viseme data
    audio_data = generate_audio_with_visemes(text)
    
    if not audio_data:
        return jsonify({'error': 'Failed to generate audio'}), 500
    
    # Set avatar to speaking state
    session['avatar_state'] = 'speaking'
    
    return jsonify({
        'audio': audio_data['audio'],
        'viseme_frames': audio_data['viseme_frames'],
        'estimated_duration': audio_data['estimated_duration'],
        'avatar_state': 'speaking',
        'message': 'Audio generated successfully'
    })

@app.route('/api/audio/stop', methods=['POST'])
def stop_audio():
    """Stop current audio and reset avatar state."""
    if 'user_id' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    session['avatar_state'] = 'idle'
    return jsonify({
        'avatar_state': 'idle',
        'message': 'Audio stopped'
    })

@app.route('/api/speech/start', methods=['POST'])
def start_speech_recognition():
    """Start speech recognition process."""
    global current_user
    
    if 'user_id' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    if not current_user or current_user['id'] != session['user_id']:
        current_user = get_or_create_user(session['username'])
    
    session['speech_recording'] = True
    session['avatar_state'] = 'listening'
    
    return jsonify({
        'recording': True,
        'avatar_state': 'listening',
        'status_message': 'Listening... (click mic to stop)'
    })

@app.route('/api/speech/stop', methods=['POST'])
def stop_speech_recognition():
    """Stop speech recognition process."""
    if 'user_id' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    session['speech_recording'] = False
    session['avatar_state'] = 'idle'
    
    return jsonify({
        'recording': False,
        'avatar_state': 'idle',
        'message': 'Speech recognition stopped'
    })

@app.route('/api/speech/transcript', methods=['POST'])
def process_speech_transcript():
    """Process speech recognition transcript."""
    global current_user
    
    if 'user_id' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    if not current_user or current_user['id'] != session['user_id']:
        current_user = get_or_create_user(session['username'])
    
    data = request.get_json()
    transcript = data.get('transcript', '').strip()
    
    if not transcript:
        return jsonify({'error': 'No transcript provided'}), 400
    
    # Process the transcript as a regular message
    conversation_history = get_recent_conversations(current_user['id'], limit=30)
    memories = retrieve_relevant_memories(current_user['id'], transcript, top_k=7)
    ai_output = get_ai_response(transcript, current_user, conversation_history, memories)
    
    response_text = ai_output.get('response', "I'm not sure how to reply.")
    
    # Log conversation
    log_conversation(current_user['id'], 'user', transcript)
    log_conversation(current_user['id'], 'model', response_text)
    
    # Update user data
    new_summary = ai_output.get('updated_summary', current_user['personality_summary'])
    new_behavioral_notes = ai_output.get('updated_behavioral_notes', current_user.get('behavioral_notes'))
    
    if new_summary != current_user['personality_summary']:
        update_user(current_user['id'], "personality_summary", new_summary)
        current_user['personality_summary'] = new_summary
    
    if new_behavioral_notes != current_user.get('behavioral_notes'):
        update_user(current_user['id'], "behavioral_notes", new_behavioral_notes)
        current_user['behavioral_notes'] = new_behavioral_notes
    
    # Generate audio response with viseme data
    audio_data = generate_audio_with_visemes(response_text)
    session['avatar_state'] = 'speaking' if audio_data else 'idle'
    
    if audio_data:
        return jsonify({
            'transcript': transcript,
            'response': response_text,
            'audio': audio_data['audio'],
            'viseme_frames': audio_data['viseme_frames'],
            'estimated_duration': audio_data['estimated_duration'],
            'avatar_state': session['avatar_state']
        })
    else:
        # Fallback to basic audio generation
        audio_b64 = generate_audio_base64(response_text)
        return jsonify({
            'transcript': transcript,
            'response': response_text,
            'audio': audio_b64,
            'avatar_state': session['avatar_state']
        })

@app.route('/api/fullscreen/toggle', methods=['POST'])
def toggle_fullscreen():
    """Toggle fullscreen mode."""
    if 'user_id' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    data = request.get_json()
    is_fullscreen = data.get('fullscreen', False)
    
    session['fullscreen'] = is_fullscreen
    
    return jsonify({
        'fullscreen': is_fullscreen,
        'message': f'Fullscreen mode {"enabled" if is_fullscreen else "disabled"}'
    })

@app.route('/api/message/append', methods=['POST'])
def append_message():
    """Handle message appending (for logging purposes)."""
    global current_user
    
    if 'user_id' not in session:
        return jsonify({'error': 'No active session'}), 400
    
    if not current_user or current_user['id'] != session['user_id']:
        current_user = get_or_create_user(session['username'])
    
    data = request.get_json()
    message = data.get('message', '').strip()
    sender = data.get('sender', 'user')  # 'user' or 'bot'
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Log the message if it's from user
    if sender == 'user':
        log_conversation(current_user['id'], 'user', message)
    
    return jsonify({
        'message': message,
        'sender': sender,
        'timestamp': datetime.datetime.now().isoformat(),
        'logged': sender == 'user'
    })

@app.route('/api/session/status', methods=['GET'])
def get_session_status():
    """Get current session status."""
    global current_user
    
    if 'user_id' not in session:
        return jsonify({'active': False, 'error': 'No active session'}), 400
    
    if not current_user or current_user['id'] != session['user_id']:
        current_user = get_or_create_user(session['username'])
    
    return jsonify({
        'active': True,
        'user': current_user,
        'avatar_state': session.get('avatar_state', 'idle'),
        'voice_enabled': session.get('voice_enabled', True),
        'fullscreen': session.get('fullscreen', False),
        'speech_recording': session.get('speech_recording', False)
    })

@app.route('/api/session/end', methods=['POST'])
def end_session():
    """End current session."""
    global current_user
    
    # Clear session data
    session.clear()
    current_user = None
    
    return jsonify({
        'message': 'Session ended successfully',
        'active': False
    })

@app.route('/logout')
def logout():
    """Logout and clear session."""
    global current_user
    session.clear()
    current_user = None
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files."""
    from flask import send_from_directory
    return send_from_directory('static', filename)

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print('Client connected')
    emit('connected', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print('Client disconnected')

@socketio.on('avatar_state_changed')
def handle_avatar_state_change(data):
    """Broadcast avatar state changes to all clients."""
    emit('avatar_state_changed', data, broadcast=True)

@socketio.on('message_sent')
def handle_message_sent(data):
    """Broadcast messages to all clients."""
    emit('message_received', data, broadcast=True)

@socketio.on('voice_toggled')
def handle_voice_toggle(data):
    """Broadcast voice toggle to all clients."""
    emit('voice_toggled', data, broadcast=True)

@socketio.on('fullscreen_toggled')
def handle_fullscreen_toggle(data):
    """Broadcast fullscreen toggle to all clients."""
    emit('fullscreen_toggled', data, broadcast=True)

def generate_smart_greeting(user_data):
    """Generate a smart greeting based on user's last visit."""
    now = datetime.datetime.now()
    
    if user_data['last_seen']:
        last_seen_dt = datetime.datetime.fromisoformat(user_data['last_seen'])
        time_since = now - last_seen_dt
        
        if time_since.days >= 1:
            # Generate a proactive check-in if it's been a while
            from ai_core import chat_model
            checkin_prompt = f"""You are checking in with your friend {user_data['username']}, who you haven't spoken to in over a day. Your last understanding of them was: "{user_data['personality_summary']}". Generate a single, gentle, short, and friendly check-in message."""
            try:
                checkin_response = chat_model.generate_content(checkin_prompt)
                return checkin_response.text
            except:
                return f"Hello again, {user_data['username']}! It's been a while. How are you doing today?"
        else:
            return f"Hello again, {user_data['username']}! What's on your mind today?"
    else:
        return f"Hello, {user_data['username']}! It's nice to meet you. How can I help you today?"

def handle_command(command):
    """Handle special commands."""
    if command.lower() == '/view':
        return view_tasks(current_user['id'])
    else:
        return "Command executed."

if __name__ == '__main__':
    socketio.run(app, debug=DEBUG, host=HOST, port=PORT, allow_unsafe_werkzeug=True)