# app/main.py
# Główny plik aplikacji Flask, zintegrowany z bazą danych i kolejką zadań RQ.

import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from redis import Redis
from rq import Queue
import json

from app.auth import login_manager, users, user_objects
from app.post_analysis import visualize_path_and_hunt_area

# --- Konfiguracja Aplikacji ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-that-should-be-changed'
app.config['UPLOAD_FOLDER'] = os.path.join('app', 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join('app', 'output')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join('app', 'database', 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Inicjalizacje ---
db = SQLAlchemy(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# Połączenie z Redis i inicjalizacja kolejki
redis_conn = Redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379'))
q = Queue(connection=redis_conn)

# --- Modele Bazy Danych ---
class Job(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    status = db.Column(db.String(50), default='queued')
    progress = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    results = db.relationship('FrameData', backref='job', lazy=True, cascade="all, delete-orphan")

class FrameData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), db.ForeignKey('job.id'), nullable=False)
    frame_number = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.Float, nullable=False)
    player_coords_json = db.Column(db.Text) # Przechowuje JSON
    stats_json = db.Column(db.Text) # Przechowuje JSON
    battle_list_json = db.Column(db.Text) # Przechowuje JSON

# --- Routing ---
@app.before_first_request
def create_tables():
    # Upewnij się, że katalogi istnieją
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join('app', 'database'), exist_ok=True)
    db.create_all()

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if users.get(username) and users[username]['password'] == password:
            login_user(user_objects[username])
            return redirect(url_for('dashboard'))
        flash('Nieprawidłowa nazwa użytkownika lub hasło.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return render_template('dashboard.html', jobs=jobs)

@app.route('/start_analysis', methods=['POST'])
@login_required
def start_analysis_route():
    # Import zadania tutaj, aby uniknąć cyklicznych importów
    from app.analysis import run_analysis

    source_type = request.form.get('source_type')
    source_data = request.form.get('source_data')
    frame_skip = int(request.form.get('frame_skip', 0))
    job_id = str(uuid.uuid4())
    upload_path = None

    if source_type == 'upload':
        file = request.files.get('source_file')
        if not file or file.filename == '':
            return jsonify({'error': 'Nie wybrano pliku'}), 400
        filename = secure_filename(f"{job_id}_{file.filename}")
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        source_data = filename
    
    # Utwórz wpis w bazie danych dla nowego zadania
    new_job = Job(id=job_id)
    db.session.add(new_job)
    db.session.commit()

    # Dodaj zadanie do kolejki RQ
    q.enqueue(run_analysis, job_id, source_type, source_data, frame_skip, upload_path, job_timeout=3600)
    
    return jsonify({'job_id': job_id})

@app.route('/status/<job_id>')
@login_required
def status_route(job_id):
    job = Job.query.get(job_id)
    if job:
        return jsonify({'status': job.status, 'progress': job.progress})
    return jsonify({'status': 'not_found', 'progress': 0})

@app.route('/results/<job_id>')
@login_required
def results_page(job_id):
    job = Job.query.get_or_404(job_id)
    if job.status != 'completed':
        flash('Analiza nie została jeszcze zakończona.')
        return redirect(url_for('dashboard'))

    frame_data = FrameData.query.filter_by(job_id=job_id).order_by(FrameData.frame_number).all()
    
    coords = [json.loads(fd.player_coords_json) for fd in frame_data if fd.player_coords_json]
    # Filtruj tylko poprawne współrzędne (x, y)
    path_coords = [(c['x'], c['y']) for c in coords if c and 'x' in c and 'y' in c]

    # Generuj wizualizację, jeśli nie istnieje
    vis_filename = f"{job_id}_path.png"
    vis_filepath = os.path.join(app.config['OUTPUT_FOLDER'], vis_filename)
    if not os.path.exists(vis_filepath) and len(path_coords) > 1:
        visualize_path_and_hunt_area(path_coords, 'map.png', vis_filepath)

    return render_template('results.html', job=job, frame_count=len(frame_data), vis_image_url=url_for('get_output_file', filename=vis_filename))

@app.route('/output/<filename>')
@login_required
def get_output_file(filename):
    """Serwuje pliki z katalogu wyjściowego (np. wizualizacje)."""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
