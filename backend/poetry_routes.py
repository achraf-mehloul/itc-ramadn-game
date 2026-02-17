from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from backend.data import CODING_CONTESTANTS
from backend.models import has_user_voted_poetry, save_poetry_vote, get_poetry_vote_results, get_all_teams

poetry_bp = Blueprint('poetry', __name__)

@poetry_bp.route('/poetry-competition', methods=['GET', 'POST'])
def poetry_competition():
    """مسابقة التصويت على أفضل مشروع"""
    if request.method == 'POST':
        contestant_id = request.form.get('contestant_id')
        first_name = session.get('first_name', '').strip().title()
        last_name = session.get('last_name', '').strip().title()
        team_id = session.get('team_id')
        
        if not first_name or not last_name:
            return render_template('code_competition.html',
                                 contestants=[],
                                 teams=get_all_teams(),
                                 error='الرجاء إدخال الاسم واللقب',
                                 ask_name=True)
        
        if has_user_voted_poetry(first_name, last_name):
            return render_template('code_competition.html',
                                 contestants=[],
                                 teams=get_all_teams(),
                                 error='لقد قمت بالتصويت مسبقاً',
                                 user_name=f"{first_name} {last_name}")
        
        if contestant_id:
            save_poetry_vote(first_name, last_name, contestant_id, team_id)
            flash('تم التصويت بنجاح', 'success')
            return redirect(url_for('poetry.poetry_results'))
    
    teams = get_all_teams()  
    
    if 'first_name' in session and 'last_name' in session:
        first_name = session['first_name']
        last_name = session['last_name']
        
        if has_user_voted_poetry(first_name, last_name):
            return render_template('code_competition.html',
                                 contestants=teams,
                                 error='لقد قمت بالتصويت مسبقاً',
                                 user_name=f"{first_name} {last_name}")
        
        return render_template('code_competition.html',
                             contestants=teams,
                             user_name=f"{first_name} {last_name}")
    
    return render_template('code_competition.html',
                         contestants=teams,
                         ask_name=True)

@poetry_bp.route('/save-user-info', methods=['POST'])
def save_user_info():
    """حفظ معلومات المستخدم للتصويت"""
    first_name = request.form.get('first_name', '').strip().title()
    last_name = request.form.get('last_name', '').strip().title()
    
    if first_name and last_name:
        session['first_name'] = first_name
        session['last_name'] = last_name
    
    return redirect(url_for('poetry.poetry_competition'))

@poetry_bp.route('/vote_results')
def poetry_results():
    """نتائج التصويت"""
    vote_dict, total_votes = get_poetry_vote_results()
    
    all_teams = get_all_teams()
    
    teams_with_votes = []
    for team in all_teams:
        team_dict = dict(team)
        votes = vote_dict.get(f"team_{team['id']}", 0)
        team_dict['votes'] = votes
        team_dict['percentage'] = (votes / total_votes * 100) if total_votes > 0 else 0
        teams_with_votes.append(team_dict)
    
    teams_with_votes.sort(key=lambda x: x['votes'], reverse=True)
    
    return render_template('code_results.html',
                         contestants=teams_with_votes,
                         total_votes=total_votes)