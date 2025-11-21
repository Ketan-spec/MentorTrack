"""
Setup script to add sample data to MentorTrack database
Run this after creating accounts to set up mentorships
"""

import sqlite3
from datetime import datetime, timedelta

DB_NAME = "mentortrack.db"

def setup_sample_mentorships():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get all mentors and mentees
    mentors = cur.execute("SELECT * FROM users WHERE role = 'mentor'").fetchall()
    mentees = cur.execute("SELECT * FROM users WHERE role = 'mentee'").fetchall()
    
    if not mentors or not mentees:
        print("Please create at least one mentor and one mentee account first!")
        print("Go to /signup and create accounts")
        conn.close()
        return
    
    # Create mentorships
    for i, mentee in enumerate(mentees):
        mentor = mentors[i % len(mentors)]  # Distribute mentees among mentors
        
        # Check if mentorship exists
        existing = cur.execute("""
            SELECT * FROM mentorships 
            WHERE mentor_id = ? AND mentee_id = ?
        """, (mentor['id'], mentee['id'])).fetchone()
        
        if not existing:
            cur.execute("""
                INSERT INTO mentorships (mentor_id, mentee_id, progress)
                VALUES (?, ?, ?)
            """, (mentor['id'], mentee['id'], 25))  # 25% progress
            
            mentorship_id = cur.lastrowid
            
            # Add sample tasks
            tasks = [
                ("Complete Python Basics", "Learn Python fundamentals and syntax", "assigned"),
                ("Build a Web Scraper", "Create a web scraper using BeautifulSoup", "in_progress"),
                ("Data Analysis Project", "Analyze a dataset and create visualizations", "assigned")
            ]
            
            for title, desc, status in tasks:
                deadline = datetime.now() + timedelta(days=14)
                cur.execute("""
                    INSERT INTO tasks (mentorship_id, title, description, deadline, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (mentorship_id, title, desc, deadline.strftime('%Y-%m-%d'), status))
            
            # Add sample session
            session_date = datetime.now() + timedelta(days=3)
            cur.execute("""
                INSERT INTO sessions (mentorship_id, title, session_date, meeting_link)
                VALUES (?, ?, ?, ?)
            """, (mentorship_id, "Weekly Check-in", session_date.strftime('%Y-%m-%d %H:%M'), "https://meet.google.com/sample"))
            
            print(f"✓ Created mentorship: {mentor['full_name']} → {mentee['full_name']}")
    
    # Add sample resources for mentors
    for mentor in mentors:
        resources = [
            ("Python Documentation", "https://docs.python.org/3/", "documentation"),
            ("Web Development Course", "https://www.youtube.com/watch?v=example", "video"),
        ]
        
        for title, url, res_type in resources:
            cur.execute("""
                INSERT INTO resources (mentor_id, title, url, resource_type)
                VALUES (?, ?, ?, ?)
            """, (mentor['id'], title, url, res_type))
        
        print(f"✓ Added resources for {mentor['full_name']}")
    
    conn.commit()
    conn.close()
    print("\n✅ Sample data setup complete!")
    print("You can now login and see the full functionality")

if __name__ == "__main__":
    print("Setting up sample data for MentorTrack...")
    setup_sample_mentorships()