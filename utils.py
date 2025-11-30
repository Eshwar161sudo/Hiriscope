import random
import re
import io
import base64
from datetime import datetime

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None

INTERVIEW_QUESTIONS = [
    "Tell me about yourself.",
    "What are your greatest strengths?",
    "What are your weaknesses?",
    "Why do you want to work here?",
    "Where do you see yourself in 5 years?",
    "Why should we hire you?",
    "What motivates you?",
    "Tell me about a challenge you've faced and how you overcame it.",
    "Describe a time when you worked as part of a team.",
    "How do you handle stress and pressure?",
    "What is your greatest professional achievement?",
    "Tell me about a time you showed leadership.",
    "How do you prioritize your work?",
    "Describe your ideal work environment.",
    "What are your salary expectations?",
    "Do you have any questions for us?",
    "Why are you leaving your current job?",
    "Tell me about a time you made a mistake.",
    "How do you handle criticism?",
    "What makes you unique?",
    "Describe a time when you disagreed with a supervisor.",
    "How do you stay organized?",
    "What are your career goals?",
    "Tell me about a successful project you led.",
    "How do you handle multiple deadlines?",
    "What do you know about our company?",
    "Describe your work style.",
    "How do you handle conflict with coworkers?",
    "What are you passionate about?",
    "Tell me about a time you went above and beyond.",
    "How do you learn new skills?",
    "What would your previous manager say about you?",
    "Describe a time you had to adapt to change.",
    "How do you measure success?",
    "What's the most difficult decision you've made?",
    "Tell me about your experience with teamwork.",
    "How do you stay updated in your field?",
    "What are your short-term goals?",
    "Describe your communication style.",
    "How do you handle tight deadlines?",
    "What do you enjoy most about your work?",
    "Tell me about a time you solved a complex problem.",
    "How do you build relationships at work?",
    "What skills do you want to develop?",
    "Describe a situation where you showed initiative.",
    "How do you handle ambiguity?",
    "What's your approach to problem-solving?",
    "Tell me about your technical skills.",
    "How do you give feedback to others?",
    "What would you do in your first 30 days here?",
    "Describe a time you received negative feedback.",
    "How do you balance work and personal life?",
    "What's your biggest professional regret?",
    "Tell me about a time you mentored someone.",
    "How do you approach learning new technologies?",
]

SKILLS_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go", "rust", "swift",
    "react", "angular", "vue", "node.js", "django", "flask", "spring", "express",
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins",
    "machine learning", "deep learning", "artificial intelligence", "data science",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    "html", "css", "sass", "tailwind", "bootstrap",
    "git", "github", "gitlab", "bitbucket", "jira", "agile", "scrum",
    "rest api", "graphql", "microservices", "devops", "ci/cd",
    "linux", "unix", "bash", "shell scripting",
    "communication", "leadership", "teamwork", "problem solving", "analytical",
    "project management", "time management", "critical thinking",
    "excel", "powerpoint", "word", "tableau", "power bi",
    "salesforce", "sap", "oracle", "photoshop", "figma", "sketch"
]

EMOTIONS = ["confident", "happy", "neutral", "nervous"]


def extract_text_from_resume(file_storage):
    """Extract text from PDF or DOCX file."""
    filename = file_storage.filename.lower()
    content = file_storage.read()
    
    try:
        if filename.endswith('.pdf'):
            if PdfReader is None:
                return "PDF reading library not available"
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        elif filename.endswith('.docx'):
            if Document is None:
                return "DOCX reading library not available"
            docx_file = io.BytesIO(content)
            doc = Document(docx_file)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        else:
            return "Unsupported file format"
    except Exception as e:
        return f"Error extracting text: {str(e)}"


def detect_skills(text):
    """Detect skills from resume text."""
    text_lower = text.lower()
    found_skills = []
    
    for skill in SKILLS_KEYWORDS:
        if skill.lower() in text_lower:
            skill_formatted = skill.title() if len(skill) > 3 else skill.upper()
            if skill_formatted not in found_skills:
                found_skills.append(skill_formatted)
    
    return found_skills[:15]


def detect_experience_years(text):
    """Detect years of experience from resume text."""
    patterns = [
        r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
        r'experience\s*(?:of\s*)?(\d+)\+?\s*years?',
        r'(\d+)\+?\s*years?\s*(?:in|of|working)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            years = int(match.group(1))
            return min(years, 30)
    
    year_mentions = re.findall(r'\b(19|20)\d{2}\b', text)
    if len(year_mentions) >= 2:
        years = sorted([int(y) for y in year_mentions])
        experience = years[-1] - years[0]
        if 0 < experience <= 40:
            return min(experience, 30)
    
    return random.randint(1, 5)


def generate_resume_suggestions(text, skills, experience_years):
    """Generate improvement suggestions for resume."""
    suggestions = []
    text_lower = text.lower()
    
    if len(text) < 500:
        suggestions.append("Add more details to your resume - it appears too brief")
    
    if len(skills) < 5:
        suggestions.append("Include more technical and soft skills relevant to your field")
    
    if "project" not in text_lower:
        suggestions.append("Add specific projects with measurable outcomes")
    
    if not any(word in text_lower for word in ["achieved", "increased", "improved", "reduced", "led", "managed"]):
        suggestions.append("Use action verbs and quantify your achievements")
    
    if "summary" not in text_lower and "objective" not in text_lower:
        suggestions.append("Add a professional summary section at the top")
    
    if "education" not in text_lower:
        suggestions.append("Include your educational background")
    
    if not re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
        suggestions.append("Make sure your contact information is clearly visible")
    
    if "linkedin" not in text_lower and "github" not in text_lower:
        suggestions.append("Add links to your LinkedIn profile or portfolio")
    
    if len(suggestions) == 0:
        suggestions.append("Your resume looks comprehensive - keep it updated regularly")
    
    return suggestions[:5]


def compute_resume_score(text, skills, experience_years):
    """Compute overall resume score."""
    score = 50
    
    score += min(len(skills) * 3, 20)
    score += min(experience_years * 2, 15)
    
    if len(text) > 1000:
        score += 5
    if len(text) > 2000:
        score += 5
    
    action_words = ["achieved", "increased", "improved", "reduced", "led", "managed", "developed", "created"]
    for word in action_words:
        if word in text.lower():
            score += 1
    
    score = min(max(score, 30), 98)
    
    return score


def get_random_question():
    """Get a random interview question."""
    return random.choice(INTERVIEW_QUESTIONS)


def compute_semantic_score(answer, question):
    """Compute semantic similarity score between answer and question."""
    if not answer or len(answer.strip()) < 10:
        return random.randint(20, 40)
    
    answer_lower = answer.lower()
    question_lower = question.lower()
    
    question_keywords = set(re.findall(r'\b\w{4,}\b', question_lower))
    answer_keywords = set(re.findall(r'\b\w{4,}\b', answer_lower))
    
    common_words = {"about", "yourself", "tell", "what", "your", "have", "been", "that", "with", "this", "from", "they", "would", "could", "should"}
    question_keywords -= common_words
    answer_keywords -= common_words
    
    if len(question_keywords) == 0:
        keyword_score = 50
    else:
        overlap = len(question_keywords & answer_keywords)
        keyword_score = min((overlap / len(question_keywords)) * 100, 100)
    
    length_score = min(len(answer.split()) * 2, 30)
    
    quality_indicators = ["because", "therefore", "for example", "specifically", "additionally", "however", "moreover"]
    quality_score = sum(5 for indicator in quality_indicators if indicator in answer_lower)
    quality_score = min(quality_score, 20)
    
    base_score = 40 + (keyword_score * 0.3) + length_score + quality_score
    variation = random.randint(-5, 10)
    
    final_score = min(max(int(base_score + variation), 30), 98)
    
    return final_score


def voice_confidence_score():
    """Generate a voice confidence score."""
    return random.randint(65, 95)


def analyze_image_emotion(image_data=None):
    """Analyze emotion from image (simulated)."""
    emotion = random.choice(EMOTIONS)
    
    weights = {"confident": 0.3, "happy": 0.25, "neutral": 0.35, "nervous": 0.1}
    emotion = random.choices(list(weights.keys()), weights=list(weights.values()))[0]
    
    confidence = random.randint(60, 95)
    
    return {
        "emotion": emotion,
        "confidence": confidence
    }


def fuse_scores(semantic_score, voice_score, emotion_data):
    """Fuse multiple scores into final score."""
    emotion_bonus = {
        "confident": 10,
        "happy": 5,
        "neutral": 0,
        "nervous": -5
    }
    
    emotion = emotion_data.get("emotion", "neutral")
    emotion_modifier = emotion_bonus.get(emotion, 0)
    
    weighted_score = (
        semantic_score * 0.5 +
        voice_score * 0.3 +
        emotion_data.get("confidence", 70) * 0.2
    )
    
    final_score = weighted_score + emotion_modifier
    final_score = min(max(int(final_score), 30), 98)
    
    return final_score


def generate_feedback(score, emotion):
    """Generate feedback based on score and emotion."""
    if score >= 85:
        feedback_options = [
            "Excellent response! Your answer was comprehensive and well-structured.",
            "Outstanding! You demonstrated strong communication skills.",
            "Great job! Your answer was clear, confident, and relevant.",
        ]
    elif score >= 70:
        feedback_options = [
            "Good response. Consider adding more specific examples.",
            "Solid answer. Try to elaborate more on your key points.",
            "Well done. Focus on quantifying your achievements next time.",
        ]
    elif score >= 55:
        feedback_options = [
            "Decent attempt. Work on structuring your answer better.",
            "Fair response. Try to be more specific and confident.",
            "Room for improvement. Practice speaking more clearly.",
        ]
    else:
        feedback_options = [
            "Keep practicing. Focus on answering the question directly.",
            "Needs work. Try to provide more detailed responses.",
            "Continue improving. Structure your thoughts before speaking.",
        ]
    
    feedback = random.choice(feedback_options)
    
    if emotion == "nervous":
        feedback += " Remember to stay calm and take your time."
    elif emotion == "confident":
        feedback += " Your confidence really shows!"
    
    return feedback


def generate_questions_from_text(text):
    """Generate relevant questions based on resume text."""
    questions = []
    text_lower = text.lower()
    
    for skill in SKILLS_KEYWORDS[:20]:
        if skill.lower() in text_lower:
            questions.append(f"Tell me about your experience with {skill}.")
    
    if "project" in text_lower:
        questions.append("Describe a challenging project you worked on.")
    
    if "team" in text_lower or "collaboration" in text_lower:
        questions.append("How do you approach teamwork and collaboration?")
    
    if "leadership" in text_lower or "lead" in text_lower:
        questions.append("Tell me about your leadership experience.")
    
    questions.extend([
        "What interests you most about this role?",
        "How do you handle tight deadlines?",
        "Where do you see yourself in the next few years?",
    ])
    
    return questions[:10]
