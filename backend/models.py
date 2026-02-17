from backend.db import get_db
import psycopg2.extras

def save_student_result(first_name, last_name, score, total_questions, team_id=None):
    """Save student result to database and return student info"""
    percentage = (score / total_questions) * 100
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, score, team_id FROM students WHERE first_name = %s AND last_name = %s',
            (first_name, last_name)
        )
        existing_student = cursor.fetchone()
        
        if existing_student:
            if score > existing_student[1]: 
                cursor.execute(
                    '''UPDATE students SET score = %s, total_questions = %s, 
                       percentage = %s, team_id = COALESCE(%s, team_id), 
                       timestamp = CURRENT_TIMESTAMP WHERE id = %s''',
                    (score, total_questions, percentage, team_id, existing_student[0])
                )
                student_id = existing_student[0]
                
                if existing_student[2] or team_id:
                    team_to_update = team_id or existing_student[2]
                    update_team_points(team_to_update, score)
            else:
                student_id = existing_student[0]
        else:
            cursor.execute(
                '''INSERT INTO students 
                   (first_name, last_name, team_id, score, total_questions, percentage) 
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id''',
                (first_name, last_name, team_id, score, total_questions, percentage)
            )
            student_id = cursor.fetchone()[0]
            
            if team_id:
                update_team_points(team_id, score)
        
        cursor.execute(
            'INSERT INTO quiz_attempts (student_id, team_id, score, total_questions) VALUES (%s, %s, %s, %s)',
            (student_id, team_id, score, total_questions)
        )
        
        conn.commit()
    
    return student_id

def get_leaderboard(limit=50):
    """Get leaderboard sorted by score"""
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('''
            SELECT first_name, last_name, score, total_questions, percentage, 
                   TO_CHAR(timestamp, 'YYYY-MM-DD') as timestamp, team_id
            FROM students 
            ORDER BY score DESC, percentage DESC, last_name ASC, first_name ASC
            LIMIT %s
        ''', (limit,))
        return cursor.fetchall()

def get_student_rank(first_name, last_name):
    """Get student's rank in the leaderboard"""
    leaderboard = get_leaderboard(1000)
    for rank, student in enumerate(leaderboard, 1):
        if student['first_name'] == first_name and student['last_name'] == last_name:
            return rank, len(leaderboard)
    return None, len(leaderboard)

def get_student_stats(first_name, last_name):
    """Get detailed statistics for a student"""
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('''
            SELECT s.first_name, s.last_name, s.score, s.total_questions, s.percentage, 
                   TO_CHAR(s.timestamp, 'YYYY-MM-DD') as timestamp, s.team_id, t.team_name,
                   (SELECT COUNT(*) FROM quiz_attempts WHERE student_id = s.id) as attempts,
                   (SELECT MAX(score) FROM quiz_attempts WHERE student_id = s.id) as best_score,
                   (SELECT AVG(score) FROM quiz_attempts WHERE student_id = s.id) as average_score
            FROM students s
            LEFT JOIN teams t ON s.team_id = t.id
            WHERE s.first_name = %s AND s.last_name = %s
            GROUP BY s.id, t.id
        ''', (first_name, last_name))
        return cursor.fetchone()

def create_team(team_name, leader_first_name, leader_last_name, description, technologies, project_title):
    """إنشاء فريق جديد"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM teams WHERE team_name = %s', (team_name,))
        if cursor.fetchone():
            return None, "اسم الفريق موجود مسبقاً"
        
        cursor.execute('''
            INSERT INTO teams 
            (team_name, leader_first_name, leader_last_name, description, technologies, project_title, members_count)
            VALUES (%s, %s, %s, %s, %s, %s, 1) RETURNING id
        ''', (team_name, leader_first_name, leader_last_name, description, technologies, project_title))
        
        team_id = cursor.fetchone()[0]
        conn.commit()
        return team_id, "تم إنشاء الفريق بنجاح"

def get_all_teams():
    """جلب كل الفرق"""
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('''
            SELECT t.*, 
                   COUNT(s.id) as actual_members,
                   (SELECT COUNT(*) FROM quiz_attempts WHERE team_id = t.id) as total_attempts
            FROM teams t
            LEFT JOIN students s ON t.id = s.team_id
            GROUP BY t.id
            ORDER BY t.total_points DESC, t.created_at ASC
        ''')
        return cursor.fetchall()

def get_team_by_id(team_id):
    """جلب فريق معين مع أعضائه"""
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cursor.execute('SELECT * FROM teams WHERE id = %s', (team_id,))
        team = cursor.fetchone()
        
        if not team:
            return None
        
        cursor.execute('''
            SELECT first_name, last_name, score 
            FROM students 
            WHERE team_id = %s 
            ORDER BY score DESC
        ''', (team_id,))
        members = cursor.fetchall()
        
        cursor.execute('''
            SELECT qa.*, s.first_name, s.last_name, 
                   TO_CHAR(qa.timestamp, 'YYYY-MM-DD HH24:MI') as timestamp
            FROM quiz_attempts qa
            JOIN students s ON qa.student_id = s.id
            WHERE qa.team_id = %s
            ORDER BY qa.timestamp DESC
            LIMIT 10
        ''', (team_id,))
        attempts = cursor.fetchall()
        
        return {
            'team': team,
            'members': members,
            'attempts': attempts,
            'members_count': len(members)
        }

def update_team_points(team_id, points_to_add):
    """تحديث نقاط الفريق"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE teams SET total_points = total_points + %s WHERE id = %s', (points_to_add, team_id))
        conn.commit()

def add_member_to_team(team_id, student_first_name, student_last_name):
    """إضافة عضو للفريق"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM students 
            WHERE first_name = %s AND last_name = %s
        ''', (student_first_name, student_last_name))
        
        student = cursor.fetchone()
        
        if student:
            cursor.execute('UPDATE students SET team_id = %s WHERE id = %s', (team_id, student[0]))
            cursor.execute('UPDATE teams SET members_count = members_count + 1 WHERE id = %s', (team_id,))
            conn.commit()
            return True
        return False

def search_teams(search_term):
    """البحث عن الفرق"""
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('''
            SELECT * FROM teams 
            WHERE team_name ILIKE %s OR project_title ILIKE %s OR description ILIKE %s
            ORDER BY total_points DESC
        ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
        return cursor.fetchall()

def has_user_voted_poetry(first_name, last_name):
    """Check if user has already voted"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM poetry_votes WHERE voter_first_name = %s AND voter_last_name = %s',
            (first_name, last_name)
        )
        return cursor.fetchone() is not None

def save_poetry_vote(first_name, last_name, contestant_id, team_id=None):
    """Save user's vote"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO poetry_votes (voter_first_name, voter_last_name, team_id, contestant_id) VALUES (%s, %s, %s, %s)',
            (first_name, last_name, team_id, contestant_id)
        )
        conn.commit()

def get_poetry_vote_results():
    """Get voting results"""
    with get_db() as conn:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('''
            SELECT contestant_id, COUNT(*) as vote_count
            FROM poetry_votes 
            GROUP BY contestant_id 
            ORDER BY vote_count DESC
        ''')
        results = cursor.fetchall()
        
        vote_dict = {row['contestant_id']: row['vote_count'] for row in results}
        total_votes = sum(vote_dict.values())
        
        return vote_dict, total_votes