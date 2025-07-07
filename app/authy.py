# app/auth.py
# Moduł odpowiedzialny za logikę uwierzytelniania użytkowników.

from flask_login import LoginManager, UserMixin

# Inicjalizacja managera logowania
login_manager = LoginManager()

class User(UserMixin):
    """Prosta klasa modelu użytkownika."""
    def __init__(self, id):
        self.id = id

# Przechowywanie użytkowników w pamięci (zgodnie ze specyfikacją)
# W systemie produkcyjnym należałoby użyć bazy danych.
users = {'admin': {'password': 'password'}}
user_objects = {'admin': User('admin')}

@login_manager.user_loader
def load_user(user_id):
    """Funkcja do wczytywania użytkownika na podstawie jego ID."""
    return user_objects.get(user_id)
