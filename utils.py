import os
from flask import current_app
from werkzeug.utils import secure_filename
from PIL import Image
import uuid

# Конфигурация
UPLOAD_FOLDER = "static/uploads/parts"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "heic"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_FILES = 20

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_upload_path():
    upload_path = os.path.join(current_app.root_path, UPLOAD_FOLDER)
    os.makedirs(upload_path, exist_ok=True)
    return upload_path

def generate_unique_filename(original_filename):
    ext = original_filename.rsplit('.', 1)[1].lower()
    unique_id = uuid.uuid4().hex
    return f"{unique_id}.{ext}"