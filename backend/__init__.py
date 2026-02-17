from flask import Flask
from backend.db import init_db

def create_app():
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    
    app.secret_key = 'your_secret_key_here_ramadan_2026'
    app.config['DATABASE'] = 'ramadan_coding.db'  
    
    with app.app_context():
        init_db()
        print("✅ Database initialized within app context")
    
    from backend.quiz_routes import quiz_bp
    from backend.poetry_routes import poetry_bp
    from backend.members_routes import members_bp
    
    app.register_blueprint(quiz_bp)
    app.register_blueprint(poetry_bp)
    app.register_blueprint(members_bp)
    
    return app