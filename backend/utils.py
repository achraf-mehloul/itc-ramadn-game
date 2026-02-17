def get_rank_info(score, total_questions):
    """Determine rank based on score"""
    percentage = (score / total_questions) * 100
    
    if percentage >= 90:
        return {"rank": "مبرمج محترف", "level": "elite", "icon": "🏆", "color": "#FFD700"}
    elif percentage >= 75:
        return {"rank": "مبرمج متقدم", "level": "advanced", "icon": "🥈", "color": "#C0C0C0"}
    elif percentage >= 60:
        return {"rank": "مبرمج متوسط", "level": "intermediate", "icon": "🥉", "color": "#CD7F32"}
    elif percentage >= 40:
        return {"rank": "مبرمج مبتدئ", "level": "beginner", "icon": "🌱", "color": "#4a569d"}
    else:
        return {"rank": "متدرّب", "level": "new", "icon": "📚", "color": "#6C757D"}

def format_datetime(date_str):
    """تنسيق التاريخ"""
    if not date_str:
        return ""
    return date_str[:10]  