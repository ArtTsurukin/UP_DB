import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename
from PIL import Image


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def allowed_video(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_VIDEO_EXTENSIONS']


def get_upload_path(part_id=None):
    if part_id:
        # Путь к конкретной папке детали
        upload_path = os.path.join(
            current_app.root_path,
            current_app.config['UPLOAD_FOLDER'],
            str(part_id)
        )
    else:
        # Общий путь (для временных файлов или других целей)
        upload_path = os.path.join(
            current_app.root_path,
            current_app.config['UPLOAD_FOLDER']
        )

    os.makedirs(upload_path, exist_ok=True)
    return upload_path


def get_video_upload_path(part_id):
    """Получает путь к папке video для конкретной детали"""
    video_path = os.path.join(
        current_app.root_path,
        current_app.config['UPLOAD_FOLDER'],
        str(part_id),
        'video'
    )
    os.makedirs(video_path, exist_ok=True)
    return video_path


def generate_unique_filename(original_filename):
    ext = original_filename.rsplit('.', 1)[1].lower()
    unique_id = uuid.uuid4().hex
    return f"{unique_id}.{ext}"


def delete_part_folder(part_id):
    """Удаляет папку с изображениями и видео детали"""
    try:
        folder_path = os.path.join(
            current_app.root_path,
            current_app.config['UPLOAD_FOLDER'],
            str(part_id)
        )
        if os.path.exists(folder_path):
            import shutil
            shutil.rmtree(folder_path)
            return True
    except Exception as e:
        print(f"Ошибка при удалении папки: {e}")
        return False


def delete_image_file(part_id, filename):
    """Удаляет конкретный файл изображения"""
    try:
        file_path = os.path.join(
            get_upload_path(part_id),
            filename
        )
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        print(f"Ошибка при удалении файла: {e}")
        return False


def delete_video_file(part_id, filename):
    """Удаляет конкретный видео файл"""
    try:
        file_path = os.path.join(
            get_video_upload_path(part_id),
            filename
        )
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        print(f"Ошибка при удалении видео файла: {e}")
        return False