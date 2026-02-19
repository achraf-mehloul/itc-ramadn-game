from backend.db import get_db
import sqlite3

def save_student_result(first_name, last_name, score, total_questions, team_id=None):
    """Save student result to database and return student info"""
    percentage = (score / total_questions) * 100
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if student already exists
        cursor.execute(
            'SELECT id, score, team_id FROM students WHERE first_name = ? AND last_name = ?',
            (first_name, last_name)
        )
        existing_student = cursor.fetchone()
        
        if existing_student:
            # Update if new score is higher
            if score > existing_student['score']:
                cursor.execute(
                    '''UPDATE students SET score = ?, total_questions = ?, 
                       percentage = ?, team_id = COALESCE(?, team_id), 
                       timestamp = CURRENT_TIMESTAMP WHERE id = ?''',
                    (score, total_questions, percentage, team_id, existing_student['id'])
                )
                student_id = existing_student['id']
                
                # Update team points if student is in a team
                if existing_student['team_id'] or team_id:
                    team_to_update = team_id or existing_student['team_id']
                    update_team_points(team_to_update, score)
            else:
                student_id = existing_student['id']
        else:
            # Insert new student
            cursor.execute(
                '''INSERT INTO students 
                   (first_name, last_name, team_id, score, total_questions, percentage) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (first_name, last_name, team_id, score, total_questions, percentage)
            )
            student_id = cursor.lastrowid
            
            # Update team points if student is in a team
            if team_id:
                update_team_points(team_id, score)
        
        # Record quiz attempt
        cursor.execute(
            'INSERT INTO quiz_attempts (student_id, team_id, score, total_questions) VALUES (?, ?, ?, ?)',
            (student_id, team_id, score, total_questions)
        )
        
        conn.commit()
    
    return student_id

def get_leaderboard(limit=50):
    """Get leaderboard sorted by score"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT first_name, last_name, score, total_questions, percentage, timestamp, team_id
            FROM students 
            ORDER BY score DESC, percentage DESC, last_name ASC, first_name ASC
            LIMIT ?
        ''', (limit,))
        
        # Convert to list of dicts for easier access
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                'first_name': row['first_name'],
                'last_name': row['last_name'],
                'score': row['score'],
                'total_questions': row['total_questions'],
                'percentage': row['percentage'],
                'timestamp': row['timestamp'],
                'team_id': row['team_id']
            })
        return result

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
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.first_name, s.last_name, s.score, s.total_questions, s.percentage, 
                   s.timestamp, s.team_id, t.team_name,
                   (SELECT COUNT(*) FROM quiz_attempts WHERE student_id = s.id) as attempts,
                   (SELECT MAX(score) FROM quiz_attempts WHERE student_id = s.id) as best_score,
                   (SELECT AVG(score) FROM quiz_attempts WHERE student_id = s.id) as average_score
            FROM students s
            LEFT JOIN teams t ON s.team_id = t.id
            WHERE s.first_name = ? AND s.last_name = ?
            GROUP BY s.id
        ''', (first_name, last_name))
        
        row = cursor.fetchone()
        if row:
            return {
                'first_name': row['first_name'],
                'last_name': row['last_name'],
                'score': row['score'],
                'total_questions': row['total_questions'],
                'percentage': row['percentage'],
                'timestamp': row['timestamp'],
                'team_id': row['team_id'],
                'team_name': row['team_name'],
                'attempts': row['attempts'],
                'best_score': row['best_score'],
                'average_score': row['average_score']
            }
        return None

def create_team(team_name, leader_first_name, leader_last_name, description, technologies, project_title):
    """إنشاء فريق جديد"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if team name already exists
        cursor.execute('SELECT id FROM teams WHERE team_name = ?', (team_name,))
        if cursor.fetchone():
            return None, "اسم الفريق موجود مسبقاً"
        
        cursor.execute('''
            INSERT INTO teams 
            (team_name, leader_first_name, leader_last_name, description, technologies, project_title, members_count)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (team_name, leader_first_name, leader_last_name, description, technologies, project_title))
        
        team_id = cursor.lastrowid
        conn.commit()
        return team_id, "تم إنشاء الفريق بنجاح"

def get_all_teams():
    """جلب كل الفرق"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.*, 
                   COUNT(s.id) as actual_members,
                   (SELECT COUNT(*) FROM quiz_attempts WHERE team_id = t.id) as total_attempts
            FROM teams t
            LEFT JOIN students s ON t.id = s.team_id
            GROUP BY t.id
            ORDER BY t.total_points DESC, t.created_at ASC
        ''')
        
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                'id': row['id'],
                'team_name': row['team_name'],
                'leader_first_name': row['leader_first_name'],
                'leader_last_name': row['leader_last_name'],
                'description': row['description'],
                'technologies': row['technologies'],
                'project_title': row['project_title'],
                'members_count': row['members_count'],
                'total_points': row['total_points'],
                'created_at': row['created_at'],
                'actual_members': row['actual_members'],
                'total_attempts': row['total_attempts']
            })
        return result

def get_team_by_id(team_id):
    """جلب فريق معين مع أعضائه"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get team info
        cursor.execute('SELECT * FROM teams WHERE id = ?', (team_id,))
        team_row = cursor.fetchone()
        
        if not team_row:
            return None
        
        team = {
            'id': team_row['id'],
            'team_name': team_row['team_name'],
            'leader_first_name': team_row['leader_first_name'],
            'leader_last_name': team_row['leader_last_name'],
            'description': team_row['description'],
            'technologies': team_row['technologies'],
            'project_title': team_row['project_title'],
            'members_count': team_row['members_count'],
            'total_points': team_row['total_points'],
            'created_at': team_row['created_at']
        }
        
        # Get team members
        cursor.execute('''
            SELECT first_name, last_name, score 
            FROM students 
            WHERE team_id = ? 
            ORDER BY score DESC
        ''', (team_id,))
        
        members_rows = cursor.fetchall()
        members = []
        for row in members_rows:
            members.append({
                'first_name': row['first_name'],
                'last_name': row['last_name'],
                'score': row['score']
            })
        
        # Get recent attempts
        cursor.execute('''
            SELECT qa.*, s.first_name, s.last_name, qa.timestamp
            FROM quiz_attempts qa
            JOIN students s ON qa.student_id = s.id
            WHERE qa.team_id = ?
            ORDER BY qa.timestamp DESC
            LIMIT 10
        ''', (team_id,))
        
        attempts_rows = cursor.fetchall()
        attempts = []
        for row in attempts_rows:
            attempts.append({
                'id': row['id'],
                'student_id': row['student_id'],
                'team_id': row['team_id'],
                'score': row['score'],
                'total_questions': row['total_questions'],
                'timestamp': row['timestamp'],
                'first_name': row['first_name'],
                'last_name': row['last_name']
            })
        
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
        cursor.execute('UPDATE teams SET total_points = total_points + ? WHERE id = ?', (points_to_add, team_id))
        conn.commit()

def add_member_to_team(team_id, student_first_name, student_last_name):
    """إضافة عضو للفريق"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Find student by name
        cursor.execute('''
            SELECT id FROM students 
            WHERE first_name = ? AND last_name = ?
        ''', (student_first_name, student_last_name))
        
        student = cursor.fetchone()
        
        if student:
            cursor.execute('UPDATE students SET team_id = ? WHERE id = ?', (team_id, student['id']))
            cursor.execute('UPDATE teams SET members_count = members_count + 1 WHERE id = ?', (team_id,))
            conn.commit()
            return True
        return False

def search_teams(search_term):
    """البحث عن الفرق"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM teams 
            WHERE team_name LIKE ? OR project_title LIKE ? OR description LIKE ?
            ORDER BY total_points DESC
        ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
        
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                'id': row['id'],
                'team_name': row['team_name'],
                'leader_first_name': row['leader_first_name'],
                'leader_last_name': row['leader_last_name'],
                'description': row['description'],
                'technologies': row['technologies'],
                'project_title': row['project_title'],
                'members_count': row['members_count'],
                'total_points': row['total_points'],
                'created_at': row['created_at']
            })
        return result

def has_user_voted_poetry(first_name, last_name):
    """Check if user has already voted"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM poetry_votes WHERE voter_first_name = ? AND voter_last_name = ?',
            (first_name, last_name)
        )
        return cursor.fetchone() is not None

def save_poetry_vote(first_name, last_name, contestant_id, team_id=None):
    """Save user's vote"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO poetry_votes (voter_first_name, voter_last_name, team_id, contestant_id) VALUES (?, ?, ?, ?)',
            (first_name, last_name, team_id, contestant_id)
        )
        conn.commit()

def get_poetry_vote_results():
    """Get voting results"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT contestant_id, COUNT(*) as vote_count
            FROM poetry_votes 
            GROUP BY contestant_id 
            ORDER BY vote_count DESC
        ''')
        results = cursor.fetchall()
        
        vote_dict = {}
        for row in results:
            vote_dict[row['contestant_id']] = row['vote_count']
        
        total_votes = sum(vote_dict.values())
        
        return vote_dict, total_votes
def get_competition_stats():
    """جلب إحصائيات المسابقة"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as count FROM students')
        students_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM teams')
        teams_count = cursor.fetchone()['count']
        
        
        cursor.execute('SELECT COUNT(*) as count FROM quiz_attempts')
        attempts_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT MAX(score) as max_score FROM students')
        max_score_row = cursor.fetchone()
        max_score = max_score_row['max_score'] if max_score_row['max_score'] else 0
        
        return {
            'students_count': students_count,
            'teams_count': teams_count,
            'attempts_count': attempts_count,
            'max_score': max_score,
            'daily_challenges': 30,  
            'prizes': 10  
        }
