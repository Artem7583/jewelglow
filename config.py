import os

class Config:
    # Основные настройки
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-very-secret-key'
    
    # Исправленная строка подключения
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:123@localhost:5432/JewelGlow"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}