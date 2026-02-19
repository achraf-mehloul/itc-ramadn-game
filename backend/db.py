import os
from contextlib import contextmanager
from flask import current_app
import psycopg
from psycopg.rows import dict_row
import sqlite3

def get_db_connection():
    if os.environ.get('RENDER') or os.environ.get('DATABASE_URL'):
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            database_url = "postgresql://ramadan_qst_sl_user:yGnEizXLCsO47ecfU5TzPNQfLYBBUszV@dpg-d69t6bk9c44c738gpj1g-a.oregon-postgres.render.com/ramadan_qst_sl"
        conn = psycopg.connect(database_url, row_factory=dict_row)
        return conn, 'postgresql'
    else:
        conn = sqlite3.connect(current_app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        return conn, 'sqlite'

@contextmanager
def get_db():
    conn, db_type = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    db_path = current_app.config['DATABASE']
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        if db_type == 'postgresql':
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    id SERIAL PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    team_id INTEGER,
                    score INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    percentage REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS teams (
                    id SERIAL PRIMARY KEY,
                    team_name TEXT NOT NULL UNIQUE,
                    leader_first_name TEXT NOT NULL,
                    leader_last_name TEXT NOT NULL,
                    description TEXT,
                    technologies TEXT,
                    project_title TEXT,
                    members_count INTEGER DEFAULT 1,
                    total_points INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quiz_attempts (
                    id SERIAL PRIMARY KEY,
                    student_id INTEGER REFERENCES students(id),
                    team_id INTEGER REFERENCES teams(id),
                    score INTEGER,
                    total_questions INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS poetry_votes (
                    id SERIAL PRIMARY KEY,
                    voter_first_name TEXT NOT NULL,
                    voter_last_name TEXT NOT NULL,
                    team_id INTEGER REFERENCES teams(id),
                    contestant_id TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    team_id INTEGER,
                    score INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    percentage REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_name TEXT NOT NULL UNIQUE,
                    leader_first_name TEXT NOT NULL,
                    leader_last_name TEXT NOT NULL,
                    description TEXT,
                    technologies TEXT,
                    project_title TEXT,
                    members_count INTEGER DEFAULT 1,
                    total_points INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quiz_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER,
                    team_id INTEGER,
                    score INTEGER,
                    total_questions INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES students (id),
                    FOREIGN KEY (team_id) REFERENCES teams (id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS poetry_votes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voter_first_name TEXT NOT NULL,
                    voter_last_name TEXT NOT NULL,
                    team_id INTEGER,
                    contestant_id TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (team_id) REFERENCES teams (id)
                )
            ''')
        conn.commit()
        conn.close()
        print(f"Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
        if 'conn' in locals():
            conn.close()
