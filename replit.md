# HiRiscope AI – Rooman Edition

## Overview
A comprehensive full-stack AI-powered interview practice platform built with Flask. Features real-time emotion detection, speech-to-text transcription, resume analysis, and performance tracking with a modern glass-morphism UI.

## Project Structure
```
/app.py                    - Main Flask application with all routes
/utils.py                  - Utility functions for scoring, analysis, and processing
/templates/
  ├── base.html            - Base template with navigation and styling
  ├── login.html           - User login page
  ├── register.html        - User registration page
  ├── dashboard.html       - Main dashboard with statistics and charts
  ├── interview.html       - Interview practice page with camera and speech
  ├── history.html         - Interview history listing
  └── results.html         - Detailed results with charts
/static/
  ├── css/style.css        - Complete styling with glass-morphism effects
  └── js/main.js           - Frontend JavaScript for camera, speech, and UI
/database/                  - SQLite database directory (auto-created)
```

## Key Features
1. **User Authentication** - Registration, login, session management with password hashing
2. **Dashboard** - Statistics display (total interviews, best/average scores), Chart.js visualizations
3. **Interview Practice** - Real-time camera feed, emotion analysis, speech-to-text
4. **Resume Analysis** - PDF/DOCX parsing, skill detection, suggestions generation
5. **History & Results** - Past interview records with detailed performance breakdown

## Technology Stack
- **Backend**: Flask (Python), PostgreSQL database
- **Frontend**: HTML5, CSS3 (glass-morphism), Vanilla JavaScript
- **APIs**: Web Speech API, MediaDevices API (camera/microphone)
- **Libraries**: PyPDF2, python-docx, Chart.js, Werkzeug

## Database Schema
- **users**: id, name, email, password (hashed), created_at
- **interviews**: id, user_id, question, answer, score, emotion, feedback, date
- **emotion_logs**: id, user_id, interview_id, emotion, confidence, date
- **resume_analysis**: id, user_id, score, skills, experience_years, suggestions, date

## API Endpoints
- `POST /register` - User registration
- `POST /login` - User login
- `GET /logout` - User logout
- `GET /dashboard` - Dashboard page
- `GET /interview` - Interview practice page
- `GET /history` - Interview history
- `GET /results` - Results page
- `GET /api/get_question` - Get random interview question
- `POST /process_emotion` - Analyze emotion from image
- `POST /submit_answer` - Submit and analyze interview answer
- `POST /upload_resume` - Upload and analyze resume

## Running the Application
The application runs on port 5000 with Flask's development server.

## Recent Changes
- Initial project setup (November 2024)
- Implemented all core features
- Added glass-morphism UI styling
- Integrated PostgreSQL database
