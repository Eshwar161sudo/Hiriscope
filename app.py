import os
import json
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash

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
)

app = Flask(__name__)
app.secret_key = "hiriscope_secret_key_2024"


# ------------------------------------------------
# DATABASE CONNECTION (SQLite)
# ------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect("database/app.db")
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------
# CREATE REQUIRED TABLES
# ------------------------------------------------
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT NOT NULL,
            answer TEXT,
            score INTEGER DEFAULT 0,
            emotion TEXT,
            feedback TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS emotion_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            interview_id INTEGER,
            emotion TEXT,
            confidence INTEGER,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(interview_id) REFERENCES interviews(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS resume_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            score INTEGER,
            skills TEXT,
            experience_years INTEGER,
            suggestions TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# ------------------------------------------------
# LOGIN REQUIRED DECORATOR
# ------------------------------------------------
def login_required(f):
    @wraps(f)
    def secure(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return secure


# ------------------------------------------------
# AUTH PAGES
# ------------------------------------------------
@app.route("/")
def home():
    return redirect(url_for("dashboard") if "user_id" in session else "login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        if cur.fetchone():
            flash("Email already registered", "error")
            return render_template("register.html")

        hashed = generate_password_hash(password)
        cur.execute("INSERT INTO users(name, email, password) VALUES (?, ?, ?)", (name, email, hashed))
        conn.commit()

        session["user_id"] = cur.lastrowid
        session["user_name"] = name

        conn.close()
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------
# DASHBOARD
# ------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM interviews WHERE user_id=?", (user_id,))
    total_interviews = cur.fetchone()[0]

    cur.execute("SELECT MAX(score) FROM interviews WHERE user_id=?", (user_id,))
    best_score = cur.fetchone()[0] or 0

    cur.execute("SELECT AVG(score) FROM interviews WHERE user_id=?", (user_id,))
    avg_score = round(cur.fetchone()[0] or 0)

    cur.execute("""
        SELECT score, date
        FROM interviews
        WHERE user_id=?
        ORDER BY date DESC
        LIMIT 10
    """, (user_id,))
    recents_raw = cur.fetchall()
    
    # Convert rows to dicts and parse dates
    recents = []
    for r in recents_raw:
        item = dict(r)
        if isinstance(item['date'], str):
            try:
                item['date'] = datetime.strptime(item['date'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass # Keep as string if format doesn't match
        recents.append(item)

    cur.execute("""
        SELECT *
        FROM resume_analysis
        WHERE user_id=?
        ORDER BY date DESC LIMIT 1
    """, (user_id,))
    latest_resume = cur.fetchone()

    conn.close()

    chart_data = {
        "labels": [r["date"].strftime('%Y-%m-%d') if isinstance(r["date"], datetime) else str(r["date"])[:10] for r in recents[::-1]],
        "scores": [r["score"] for r in recents[::-1]]
    }

    return render_template(
        "dashboard.html",
        total_interviews=total_interviews,
        best_score=best_score,
        avg_score=avg_score,
        recent_interviews=recents,
        latest_resume=latest_resume,
        chart_data=json.dumps(chart_data),
        user_name=session["user_name"]
    )


# ------------------------------------------------
# INTERVIEW PAGE
# ------------------------------------------------
@app.route("/interview")
@login_required
def interview():
    return render_template("interview.html", user_name=session["user_name"])


# ------------------------------------------------
# GET NEW QUESTION
# ------------------------------------------------
@app.route("/api/get_question")
@login_required
def api_get_question():
    return jsonify({"success": True, "question": get_random_question()})


# ------------------------------------------------
# PROCESS EMOTION (image → emotion)
# ------------------------------------------------
@app.route("/process_emotion", methods=["POST"])
@login_required
def process_emotion():
    data = request.get_json()
    result = analyze_image_emotion(data["image"])
    return jsonify(result)


# ------------------------------------------------
# SUBMIT INTERVIEW ANSWER
# ------------------------------------------------
@app.route("/submit_answer", methods=["POST"])
@login_required
def submit_answer():
    data = request.get_json()

    question = data["question"]
    answer = data["answer"]
    emotion = data["emotion"]

    semantic_score = compute_semantic_score(answer, question)
    voice_score = voice_confidence_score()
    final_score = fuse_scores(
        semantic_score,
        voice_score,
        {"emotion": emotion, "confidence": 80}
    )
    feedback = generate_feedback(final_score, emotion)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO interviews (user_id, question, answer, score, emotion, feedback)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session["user_id"], question, answer, final_score, emotion, feedback))
    conn.commit()
    interview_id = cur.lastrowid
    conn.close()

    return jsonify({
        "success": True,
        "semantic_score": semantic_score,
        "voice_score": voice_score,
        "score": final_score,
        "feedback": feedback,
        "interview_id": interview_id
    })


# ------------------------------------------------
# HISTORY PAGE
# ------------------------------------------------
@app.route("/history")
@login_required
def history():
    user_id = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM interviews
        WHERE user_id=?
        ORDER BY date DESC
    """, (user_id,))
    all_interviews_raw = cur.fetchall()
    conn.close()
    
    all_interviews = []
    for r in all_interviews_raw:
        item = dict(r)
        if isinstance(item['date'], str):
            try:
                item['date'] = datetime.strptime(item['date'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        all_interviews.append(item)

    return render_template(
        "history.html",
        history=all_interviews,
        user_name=session["user_name"]
    )


# ------------------------------------------------
# RESUME ANALYSIS
# ------------------------------------------------
@app.route("/upload_resume", methods=["POST"])
@login_required
def upload_resume():
    file = request.files.get("resume")
    if not file:
        return jsonify({"success": False, "error": "No file"}), 400

    text = extract_text_from_resume(file)
    skills = detect_skills(text)
    years = detect_experience_years(text)
    suggestions = generate_resume_suggestions(text, skills, years)
    score = compute_resume_score(text, skills, years)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO resume_analysis(user_id, score, skills, experience_years, suggestions)
        VALUES (?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        score,
        json.dumps(skills),
        years,
        json.dumps(suggestions)
    ))
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "score": score,
        "skills": skills,
        "experience_years": years,
        "suggestions": suggestions
    })


# ------------------------------------------------
# RESULTS PAGE
# ------------------------------------------------
@app.route("/results")
@login_required
def results():
    interview_id = request.args.get("id")
    user_id = session["user_id"]
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if interview_id:
        cur.execute("SELECT * FROM interviews WHERE id=? AND user_id=?", (interview_id, user_id))
        interview_raw = cur.fetchone()
    else:
        # Get the most recent interview
        cur.execute("SELECT * FROM interviews WHERE user_id=? ORDER BY date DESC LIMIT 1", (user_id,))
        interview_raw = cur.fetchone()
    
    interview = None
    if interview_raw:
        interview = dict(interview_raw)
        if isinstance(interview['date'], str):
            try:
                interview['date'] = datetime.strptime(interview['date'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass

    emotion_data = {}
    if interview:
        # Get emotion logs for this interview
        cur.execute("SELECT emotion, COUNT(*) as count FROM emotion_logs WHERE interview_id=? GROUP BY emotion", (interview["id"],))
        emotions = cur.fetchall()
        for e in emotions:
            emotion_data[e["emotion"]] = e["count"]
            
    conn.close()
    
    return render_template(
        "results.html", 
        interview=interview, 
        emotion_data=json.dumps(emotion_data),
        user_name=session["user_name"]
    )


# ------------------------------------------------
# RUN SERVER
# ------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
