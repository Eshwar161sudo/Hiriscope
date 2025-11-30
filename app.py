import os
import json
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor

from utils import (
    extract_text_from_resume,
    detect_skills,
    detect_experience_years,
    generate_resume_suggestions,
    compute_resume_score,
    get_random_question,
    compute_semantic_score,
    voice_confidence_score,
    analyze_image_emotion,
    fuse_scores,
    generate_feedback,
    INTERVIEW_QUESTIONS
)

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'hiriscope-secret-key-2024')

def get_db_connection():
    """Get database connection."""
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    return conn

def init_db():
    """Initialize the database tables."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS interviews (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            question TEXT NOT NULL,
            answer TEXT,
            score INTEGER DEFAULT 0,
            emotion VARCHAR(50),
            feedback TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS emotion_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            interview_id INTEGER REFERENCES interviews(id),
            emotion VARCHAR(50),
            confidence INTEGER,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS resume_analysis (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            score INTEGER DEFAULT 0,
            skills TEXT,
            experience_years INTEGER DEFAULT 0,
            suggestions TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Home page - redirect to dashboard or login."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            
            if not name or not email or not password:
                flash('All fields are required.', 'error')
                return render_template('register.html')
            
            if len(password) < 6:
                flash('Password must be at least 6 characters.', 'error')
                return render_template('register.html')
            
            hashed_password = generate_password_hash(password)
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute('SELECT id FROM users WHERE email = %s', (email,))
            if cur.fetchone():
                flash('Email already registered.', 'error')
                cur.close()
                conn.close()
                return render_template('register.html')
            
            cur.execute(
                'INSERT INTO users (name, email, password) VALUES (%s, %s, %s) RETURNING id',
                (name, email, hashed_password)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            
            session['user_id'] = user_id
            session['user_name'] = name
            flash('Registration successful! Welcome to HiRiscope AI.', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Registration error: {str(e)}', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash('Email and password are required.', 'error')
                return render_template('login.html')
            
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                flash('Welcome back!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password.', 'error')
                return render_template('login.html')
                
        except Exception as e:
            flash(f'Login error: {str(e)}', 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page with statistics."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        user_id = session['user_id']
        
        cur.execute('SELECT COUNT(*) as total FROM interviews WHERE user_id = %s', (user_id,))
        total_interviews = cur.fetchone()['total']
        
        cur.execute('SELECT MAX(score) as best FROM interviews WHERE user_id = %s', (user_id,))
        result = cur.fetchone()
        best_score = result['best'] if result['best'] else 0
        
        cur.execute('SELECT AVG(score) as avg FROM interviews WHERE user_id = %s', (user_id,))
        result = cur.fetchone()
        avg_score = round(result['avg']) if result['avg'] else 0
        
        cur.execute('''
            SELECT score, date FROM interviews 
            WHERE user_id = %s 
            ORDER BY date DESC 
            LIMIT 10
        ''', (user_id,))
        recent_interviews = cur.fetchall()
        
        cur.execute('''
            SELECT * FROM resume_analysis 
            WHERE user_id = %s 
            ORDER BY date DESC 
            LIMIT 1
        ''', (user_id,))
        latest_resume = cur.fetchone()
        
        cur.close()
        conn.close()
        
        chart_data = {
            'labels': [i['date'].strftime('%m/%d') for i in reversed(recent_interviews)],
            'scores': [i['score'] for i in reversed(recent_interviews)]
        }
        
        return render_template('dashboard.html',
            total_interviews=total_interviews,
            best_score=best_score,
            avg_score=avg_score,
            recent_interviews=recent_interviews,
            latest_resume=latest_resume,
            chart_data=json.dumps(chart_data),
            user_name=session.get('user_name', 'User')
        )
        
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html',
            total_interviews=0,
            best_score=0,
            avg_score=0,
            recent_interviews=[],
            latest_resume=None,
            chart_data=json.dumps({'labels': [], 'scores': []}),
            user_name=session.get('user_name', 'User')
        )

@app.route('/interview')
@login_required
def interview():
    """Interview practice page."""
    return render_template('interview.html', user_name=session.get('user_name', 'User'))

@app.route('/history')
@login_required
def history():
    """Interview history page."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute('''
            SELECT * FROM interviews 
            WHERE user_id = %s 
            ORDER BY date DESC
        ''', (session['user_id'],))
        interviews = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('history.html', 
            interviews=interviews,
            user_name=session.get('user_name', 'User')
        )
        
    except Exception as e:
        flash(f'Error loading history: {str(e)}', 'error')
        return render_template('history.html', 
            interviews=[],
            user_name=session.get('user_name', 'User')
        )

@app.route('/results')
@login_required
def results():
    """Interview results page."""
    interview_id = request.args.get('id')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if interview_id:
            cur.execute('''
                SELECT * FROM interviews 
                WHERE id = %s AND user_id = %s
            ''', (interview_id, session['user_id']))
            interview_data = cur.fetchone()
            
            cur.execute('''
                SELECT emotion, COUNT(*) as count 
                FROM emotion_logs 
                WHERE interview_id = %s 
                GROUP BY emotion
            ''', (interview_id,))
            emotion_dist = cur.fetchall()
        else:
            cur.execute('''
                SELECT * FROM interviews 
                WHERE user_id = %s 
                ORDER BY date DESC 
                LIMIT 1
            ''', (session['user_id'],))
            interview_data = cur.fetchone()
            
            if interview_data:
                cur.execute('''
                    SELECT emotion, COUNT(*) as count 
                    FROM emotion_logs 
                    WHERE interview_id = %s 
                    GROUP BY emotion
                ''', (interview_data['id'],))
                emotion_dist = cur.fetchall()
            else:
                emotion_dist = []
        
        cur.close()
        conn.close()
        
        emotion_data = {e['emotion']: e['count'] for e in emotion_dist} if emotion_dist else {}
        
        return render_template('results.html',
            interview=interview_data,
            emotion_data=json.dumps(emotion_data),
            user_name=session.get('user_name', 'User')
        )
        
    except Exception as e:
        flash(f'Error loading results: {str(e)}', 'error')
        return render_template('results.html',
            interview=None,
            emotion_data=json.dumps({}),
            user_name=session.get('user_name', 'User')
        )

@app.route('/api/get_question', methods=['GET'])
@login_required
def api_get_question():
    """Get a random interview question."""
    try:
        question = get_random_question()
        return jsonify({'question': question, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/process_emotion', methods=['POST'])
@login_required
def process_emotion():
    """Process emotion from image."""
    try:
        data = request.get_json()
        image_data = data.get('image', '')
        interview_id = data.get('interview_id')
        
        emotion_result = analyze_image_emotion(image_data)
        
        if interview_id:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO emotion_logs (user_id, interview_id, emotion, confidence)
                VALUES (%s, %s, %s, %s)
            ''', (session['user_id'], interview_id, emotion_result['emotion'], emotion_result['confidence']))
            conn.commit()
            cur.close()
            conn.close()
        
        return jsonify(emotion_result)
        
    except Exception as e:
        return jsonify({'error': str(e), 'emotion': 'neutral', 'confidence': 50}), 500

@app.route('/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    """Submit interview answer for analysis."""
    try:
        data = request.get_json()
        question = data.get('question', '')
        answer = data.get('answer', '')
        emotion = data.get('emotion', 'neutral')
        
        semantic_score = compute_semantic_score(answer, question)
        voice_score = voice_confidence_score()
        emotion_data = {'emotion': emotion, 'confidence': data.get('emotion_confidence', 75)}
        
        final_score = fuse_scores(semantic_score, voice_score, emotion_data)
        feedback = generate_feedback(final_score, emotion)
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO interviews (user_id, question, answer, score, emotion, feedback)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (session['user_id'], question, answer, final_score, emotion, feedback))
        interview_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'score': final_score,
            'feedback': feedback,
            'semantic_score': semantic_score,
            'voice_score': voice_score,
            'interview_id': interview_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/upload_resume', methods=['POST'])
@login_required
def upload_resume():
    """Upload and analyze resume."""
    try:
        if 'resume' not in request.files:
            return jsonify({'error': 'No file uploaded', 'success': False}), 400
        
        file = request.files['resume']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected', 'success': False}), 400
        
        if not (file.filename.lower().endswith('.pdf') or file.filename.lower().endswith('.docx')):
            return jsonify({'error': 'Only PDF and DOCX files are supported', 'success': False}), 400
        
        text = extract_text_from_resume(file)
        
        if text.startswith('Error') or text.startswith('Unsupported'):
            return jsonify({'error': text, 'success': False}), 400
        
        skills = detect_skills(text)
        experience_years = detect_experience_years(text)
        suggestions = generate_resume_suggestions(text, skills, experience_years)
        score = compute_resume_score(text, skills, experience_years)
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO resume_analysis (user_id, score, skills, experience_years, suggestions)
            VALUES (%s, %s, %s, %s, %s)
        ''', (session['user_id'], score, json.dumps(skills), experience_years, json.dumps(suggestions)))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'score': score,
            'skills': skills,
            'experience_years': experience_years,
            'suggestions': suggestions
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/questions', methods=['GET'])
@login_required
def api_questions():
    """Get all interview questions."""
    return jsonify({'questions': INTERVIEW_QUESTIONS, 'success': True})

@app.after_request
def after_request(response):
    """Add headers to prevent caching and handle CORS."""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
