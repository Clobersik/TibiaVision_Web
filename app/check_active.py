# app/check_active.py
# Pomocniczy skrypt do sprawdzania, czy w systemie są aktywne zadania.
# Używany przez cron do bezpiecznego restartu aplikacji.
# Zwraca kod wyjścia 0, jeśli można bezpiecznie zrestartować.
# Zwraca kod wyjścia 1, jeśli zadanie jest w toku.

import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Konfiguracja, aby skrypt mógł połączyć się z tą samą bazą danych co aplikacja
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tibia-vision-app/app/database/app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Musimy zdefiniować model, aby SQLAlchemy wiedziało, czego szukać
class Job(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    status = db.Column(db.String(50), default='queued')
    # Reszta pól nie jest potrzebna do tego sprawdzenia
    __tablename__ = 'job' 

def check_for_active_jobs():
    """Sprawdza bazę danych w poszukiwaniu zadań ze statusem 'processing'."""
    with app.app_context():
        try:
            processing_jobs_count = Job.query.filter_by(status='processing').count()
            if processing_jobs_count > 0:
                print(f"Wykryto {processing_jobs_count} aktywnych zadan. Restart wstrzymany.")
                return 1 # Zwróć błąd, jeśli są aktywne zadania
            else:
                print("Brak aktywnych zadan. Mozna bezpiecznie zrestartowac.")
                return 0 # Zwróć sukces, jeśli jest bezpiecznie
        except Exception as e:
            print(f"Blad podczas laczenia z baza danych: {e}")
            return 1 # Na wszelki wypadek, nie restartuj, jeśli jest błąd
    
if __name__ == '__main__':
    sys.exit(check_for_active_jobs())
