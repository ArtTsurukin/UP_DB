import os
import datetime


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'TEST_KEY_SECRET_EXAMPLE'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///updb.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT settings
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(minutes=60)
    JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(weeks=2)

    # File upload settings
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
    MAX_FILES = 20
    MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
    MAX_VIDEOS = 5
    UPLOAD_FOLDER = "static/uploads/parts"
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "heic"}
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "wmv", "flv", "webm", "mkv"}


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False