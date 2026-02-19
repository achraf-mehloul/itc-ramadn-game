from backend.db import get_db
import sqlite3

def save_student_result(first_name, last_name, score, total_questions, team_id=None):
    percentage = (score / total_questions) * 100
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, score, team_id FROM students WHERE first_name = %s AND last_name = %s',
            (first_name, last_name)
        )
        existing_student = cursor.fetchone()
        if existing_student:
            if score > existing_student['score']:
                cursor.execute(
                    '''UPDATE students SET score = %s, total_questions = %s, 
                       percentage = %s, team_id = COALESCE(%s, team_id), 
                       timestamp = CURRENT_TIMESTAMP WHERE id = %s''',
                    (score, total_questions, percentage, team_id, existing_student['id'])
                )
                student_id = existing_student['id']
                if existing_student['team_id'] or team_id:
                    team_to_update = team_id or existing_student['team_id']
                    update_team_points(team_to_update, score)
            else:
                student_id = existing_student['id']
        else:
            cursor.execute(
                '''INSERT INTO students 
                   (first_name, last_name, team_id, score, total_questions, percentage) 
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id''',
                (first_name, last_name, team_id, score, total_questions, percentage)
            )
            student_id = cursor.fetchone()['id']
            if team_id:
                update_team_points(team_id, score)
        cursor.execute(
            'INSERT INTO quiz_attempts (student_id, team_id, score, total_questions) VALUES (%s, %s, %s, %s)',
            (student_id, team_id, score, total_questions)
        )
        conn.commit()
    return student_id

def get_leaderboard(limit=50):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT first_name, last_name, score, total_questions, percentage, 
                   TO_CHAR(timestamp, 'YYYY-MM-DD') as timestamp, team_id
            FROM students 
            ORDER BY score DESC, percentage DESC, last_name ASC, first_name ASC
            LIMIT %s
        ''', (limit,))
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
    leaderboard = get_leaderboard(1000)
    for rank, student in enumerate(leaderboard, 1):
        if student['first_name'] == first_name and student['last_name'] == last_name:
            return rank, len(leaderboard)
    return None, len(leaderboard)

def get_student_stats(first_name, last_name):
    with get_db() as conn:
        cursor = conn.cursor()
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
        team_id = cursor.fetchone()['id']
        conn.commit()
        return team_id, "تم إنشاء الفريق بنجاح"

def get_all_teams():
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
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM teams WHERE id = %s', (team_id,))
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
        cursor.execute('''
            SELECT first_name, last_name, score 
            FROM students 
            WHERE team_id = %s 
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
        cursor.execute('''
            SELECT qa.*, s.first_name, s.last_name, qa.timestamp
            FROM quiz_attempts qa
            JOIN students s ON qa.student_id = s.id
            WHERE qa.team_id = %s
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
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE teams SET total_points = total_points + %s WHERE id = %s', (points_to_add, team_id))
        conn.commit()

def add_member_to_team(team_id, student_first_name, student_last_name):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id FROM students 
            WHERE first_name = %s AND last_name = %s
        ''', (student_first_name, student_last_name))
        student = cursor.fetchone()
        if student:
            cursor.execute('UPDATE students SET team_id = %s WHERE id = %s', (team_id, student['id']))
            cursor.execute('UPDATE teams SET members_count = members_count + 1 WHERE id = %s', (team_id,))
            conn.commit()
            return True
        return False

def search_teams(search_term):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM teams 
            WHERE team_name ILIKE %s OR project_title ILIKE %s OR description ILIKE %s
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
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM poetry_votes WHERE voter_first_name = %s AND voter_last_name = %s',
            (first_name, last_name)
        )
        return cursor.fetchone() is not None

def save_poetry_vote(first_name, last_name, contestant_id, team_id=None):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO poetry_votes (voter_first_name, voter_last_name, team_id, contestant_id) VALUES (%s, %s, %s, %s)',
            (first_name, last_name, team_id, contestant_id)
        )
        conn.commit()

def get_poetry_vote_results():
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
