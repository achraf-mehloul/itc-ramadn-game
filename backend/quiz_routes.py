from flask import Blueprint, render_template, request, session, redirect, url_for
from backend.data import QUESTIONS
from backend.models import save_student_result, get_student_rank, get_student_stats, get_leaderboard, get_all_teams
from backend.utils import get_rank_info

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.route('/')
def index():
    top_students = get_leaderboard(5)
    teams_count = len(get_all_teams())
    return render_template('index.html', top_students=top_students, teams_count=teams_count)

@quiz_bp.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if request.method == 'POST':
        session['first_name'] = request.form['first_name'].strip().title()
        session['last_name'] = request.form['last_name'].strip().title()
        session['team_id'] = request.form.get('team_id', None)
        session['score'] = 0
        session['current_question'] = 0
        session['answers'] = []
        return redirect(url_for('quiz.question'))
    
    teams = get_all_teams()
    
    if 'first_name' in session and 'last_name' in session:
        session['score'] = 0
        session['current_question'] = 0
        session['answers'] = []
        return redirect(url_for('quiz.question'))
    
    return render_template('quiz.html', teams=teams)

@quiz_bp.route('/question', methods=['GET', 'POST'])
def question():
    if 'first_name' not in session:
        return redirect(url_for('quiz.quiz'))
    
    if request.method == 'POST':
        user_answer = request.form.get('answer')
        current_q_index = session['current_question']
        correct_answer = QUESTIONS[current_q_index]['correct']
        
        session['answers'].append({
            'question': QUESTIONS[current_q_index]['question'],
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': user_answer == correct_answer
        })
        
        if user_answer == correct_answer:
            session['score'] += 1
        
        session['current_question'] += 1
        
        if session['current_question'] >= len(QUESTIONS):
            save_student_result(
                session['first_name'], 
                session['last_name'], 
                session['score'], 
                len(QUESTIONS),
                session.get('team_id')
            )
            return redirect(url_for('quiz.results'))
    
    if session['current_question'] >= len(QUESTIONS):
        return redirect(url_for('quiz.results'))
    
    question_data = QUESTIONS[session['current_question']]
    return render_template('question.html', 
                         question=question_data,
                         question_number=session['current_question'] + 1,
                         total_questions=len(QUESTIONS))

@quiz_bp.route('/results')
def results():
    if 'first_name' not in session:
        return redirect(url_for('quiz.quiz'))
    
    score = session['score']
    total = len(QUESTIONS)
    rank_info = get_rank_info(score, total)
    student_rank, total_students = get_student_rank(session['first_name'], session['last_name'])
    student_stats = get_student_stats(session['first_name'], session['last_name'])
    leaderboard = get_leaderboard(10)
    
    return render_template('results.html',
                         first_name=session['first_name'],
                         last_name=session['last_name'],
                         score=score,
                         total=total,
                         answers=session['answers'],
                         rank_info=rank_info,
                         student_rank=student_rank,
                         total_students=total_students,
                         student_stats=student_stats,
                         leaderboard=leaderboard)

@quiz_bp.route('/leaderboard')
def leaderboard():
    search = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 20
    
    all_students = get_leaderboard(1000)
    
    if search:
        filtered_students = [
            student for student in all_students 
            if search.lower() in f"{student['first_name']} {student['last_name']}".lower()
        ]
    else:
        filtered_students = all_students
    
    total_students = len(filtered_students)
    total_pages = (total_students + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    students_page = filtered_students[start_idx:end_idx]
    
    return render_template('leaderboard.html', 
                         leaderboard=students_page,
                         total_students=total_students,
                         page=page,
                         total_pages=total_pages,
                         search=search)

@quiz_bp.route('/restart')
def restart():
    session.clear()
    return redirect(url_for('quiz.quiz'))