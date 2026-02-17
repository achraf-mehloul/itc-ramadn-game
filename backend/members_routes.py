from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from backend.models import (
    get_all_teams, get_team_by_id, create_team, 
    search_teams, add_member_to_team
)

members_bp = Blueprint('members', __name__)

@members_bp.route('/teams')
def teams_list():
    """عرض كل الفرق"""
    search = request.args.get('search', '').strip()
    
    if search:
        teams = search_teams(search)
    else:
        teams = get_all_teams()
    
    return render_template('teams_list.html', teams=teams, search=search)

@members_bp.route('/team/<int:team_id>')
def team_detail(team_id):
    """عرض صفحة فريق معين"""
    team_data = get_team_by_id(team_id)
    
    if not team_data:
        flash('الفريق غير موجود', 'error')
        return redirect(url_for('members.teams_list'))
    
    return render_template('team_detail.html', team_data=team_data)

@members_bp.route('/create-team', methods=['GET', 'POST'])
def create_team_route():
    """إنشاء فريق جديد"""
    if 'first_name' not in session or 'last_name' not in session:
        flash('الرجاء تسجيل الدخول أولاً', 'warning')
        return redirect(url_for('quiz.quiz'))
    
    if request.method == 'POST':
        team_name = request.form.get('team_name', '').strip()
        description = request.form.get('description', '').strip()
        technologies = request.form.get('technologies', '').strip()
        project_title = request.form.get('project_title', '').strip()
        
        if not team_name:
            flash('اسم الفريق مطلوب', 'error')
            return render_template('create_team.html')
        
        if not project_title:
            flash('عنوان المشروع مطلوب', 'error')
            return render_template('create_team.html')
        
        team_id, message = create_team(
            team_name=team_name,
            leader_first_name=session['first_name'],
            leader_last_name=session['last_name'],
            description=description,
            technologies=technologies,
            project_title=project_title
        )
        
        if team_id:
            session['team_id'] = team_id
            flash(message, 'success')
            return redirect(url_for('members.team_detail', team_id=team_id))
        else:
            flash(message, 'error')  
            return render_template('create_team.html')
    
    return render_template('create_team.html')

@members_bp.route('/join-team/<int:team_id>', methods=['POST'])
def join_team(team_id):
    """انضمام عضو للفريق"""
    if 'first_name' not in session or 'last_name' not in session:
        flash('الرجاء تسجيل الدخول أولاً', 'warning')
        return redirect(url_for('quiz.quiz'))
    
    success = add_member_to_team(
        team_id, 
        session['first_name'], 
        session['last_name']
    )
    
    if success:
        session['team_id'] = team_id
        flash('تم الانضمام للفريق بنجاح', 'success')
    else:
        flash('حدث خطأ أثناء الانضمام للفريق', 'error')
    
    return redirect(url_for('members.team_detail', team_id=team_id))

@members_bp.route('/my-team')
def my_team():
    """عرض فريق المستخدم الحالي"""
    team_id = session.get('team_id')
    
    if not team_id:
        flash('أنت لست عضواً في أي فريق', 'info')
        return redirect(url_for('members.teams_list'))
    
    return redirect(url_for('members.team_detail', team_id=team_id))

@members_bp.route('/six-members')
def six_members_redirect():
    return redirect(url_for('members.teams_list'))