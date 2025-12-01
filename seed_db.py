import sqlite3

def seed():
    conn = sqlite3.connect('database/app.db')
    cur = conn.cursor()
    
    # Check if user 1 exists
    cur.execute("SELECT id FROM users WHERE id=1")
    if not cur.fetchone():
        print("User 1 not found")
        return

    # Insert sample interview
    cur.execute("""
        INSERT INTO interviews (user_id, question, answer, score, emotion, feedback)
        VALUES (1, 'Tell me about yourself.', 'I am a passionate developer with experience in Python and web development. I love building applications that solve real-world problems.', 88, 'confident', 'Excellent response! Your confidence really shows.')
    """)
    interview_id = cur.lastrowid
    
    # Insert sample emotion logs
    cur.execute("INSERT INTO emotion_logs (user_id, interview_id, emotion, confidence) VALUES (1, ?, 'confident', 90)", (interview_id,))
    cur.execute("INSERT INTO emotion_logs (user_id, interview_id, emotion, confidence) VALUES (1, ?, 'happy', 85)", (interview_id,))
    cur.execute("INSERT INTO emotion_logs (user_id, interview_id, emotion, confidence) VALUES (1, ?, 'neutral', 40)", (interview_id,))
    
    conn.commit()
    conn.close()
    print(f"Inserted interview {interview_id} for user 1")

if __name__ == "__main__":
    seed()
