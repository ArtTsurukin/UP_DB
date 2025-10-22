from flask import Blueprint, render_template, request, redirect, current_app, jsonify, session
from app.extensions import db
from app.models import Part, PartImage, PartVideo
from app.utils.security import admin_required
from app.utils.file_handling import allowed_file, allowed_video, get_upload_path, get_video_upload_path, generate_unique_filename, delete_image_file, delete_video_file
from sqlalchemy import or_
import os

parts_bp = Blueprint('parts', __name__)

@parts_bp.route("/parts", methods=["GET"], strict_slashes=False)
def all_parts():
    parts = Part.query.options(db.joinedload(Part.images)).all()
    return render_template("all_parts.html", parts=parts)

@parts_bp.route("/parts/new_part", methods=["GET"], strict_slashes=False)
@admin_required
def new_part_form():
    return render_template("new_part.html")

@parts_bp.route("/parts/<int:pid>", methods=["GET"], strict_slashes=False)
def get_one_part(pid):
    try:
        part = db.session.get(Part, pid)
        return render_template("part.html", part=part)
    except Exception as e:
        return f"Деталь не найдена - {e}"

@parts_bp.route("/parts/<int:pid>", methods=["DELETE"], strict_slashes=False)
@admin_required
def delete_one_part(pid):
    try:
        to_delete = db.session.get(Part, pid)

        if not to_delete:
            return "Part not found", 404

        # Удаляем файлы изображений с диска
        for image in to_delete.images:
            delete_image_file(to_delete.id, image.filename)

        # Удаляем файлы видео с диска
        for video in to_delete.videos:
            delete_video_file(to_delete.id, video.filename)

        # Удаляем папку детали полностью
        from app.utils.file_handling import delete_part_folder
        delete_part_folder(to_delete.id)

        # Удаляем деталь (изображения и видео удалятся автоматически благодаря каскаду)
        db.session.delete(to_delete)
        db.session.commit()

        return "deleted", 200

    except Exception as e:
        db.session.rollback()
        return f"error - {e}", 500

@parts_bp.route("/parts/new_part/added", methods=["POST"], strict_slashes=False)
@admin_required
def add_part():
    try:
        # Проверяем количество файлов
        if "images" in request.files:
            files = request.files.getlist("images")
            if len(files) > current_app.config['MAX_FILES']:
                return f"Слишком много файлов. Максимум: {current_app.config['MAX_FILES']}", 400

        # Проверяем количество видео файлов
        if "videos" in request.files:
            video_files = request.files.getlist("videos")
            if len(video_files) > current_app.config['MAX_VIDEOS']:
                return f"Слишком много видео файлов. Максимум: {current_app.config['MAX_VIDEOS']}", 400

        # Обрабатываем текстовые данные
        name = request.form["name"]
        car = request.form["car"]
        part_number = request.form["part_number"]
        description = request.form["description"]
        price_in = int(request.form["price_in"])
        price_out = int(request.form["price_out"])
        quantity = int(request.form["quantity"])  # ← Добавляем количество

        # Создаем деталь
        part = Part(
            name=name,
            car=car,
            part_number=part_number,
            description=description,
            price_in=price_in,
            price_out=price_out,
            quantity=quantity  # ← Устанавливаем количество
        )

        db.session.add(part)
        db.session.flush()  # Получаем ID до коммита

        # Создаем папки для изображений и видео этой детали
        part_upload_path = get_upload_path(part.id)
        video_upload_path = get_video_upload_path(part.id)

        # Обрабатываем изображения
        if 'images' in request.files:
            files = request.files.getlist('images')

            for i, image_file in enumerate(files):
                if image_file and image_file.filename != '' and allowed_file(image_file.filename):
                    # Проверяем размер файла
                    image_file.seek(0, 2)
                    file_size = image_file.tell()
                    image_file.seek(0)

                    if file_size > current_app.config['MAX_FILE_SIZE']:
                        continue

                    # Генерируем уникальное имя
                    unique_filename = generate_unique_filename(image_file.filename)
                    file_path = os.path.join(part_upload_path, unique_filename)

                    # Сохраняем файл
                    image_file.save(file_path)

                    # Создаем запись в базе
                    part_image = PartImage(
                        part_id=part.id,
                        filename=unique_filename,
                        is_main=(i == 0)  # Первое фото - главное
                    )
                    db.session.add(part_image)

        # Обрабатываем видео
        if 'videos' in request.files:
            video_files = request.files.getlist('videos')

            for video_file in video_files:
                if video_file and video_file.filename != '' and allowed_video(video_file.filename):
                    # Проверяем размер файла
                    video_file.seek(0, 2)
                    file_size = video_file.tell()
                    video_file.seek(0)

                    if file_size > current_app.config['MAX_VIDEO_SIZE']:
                        continue

                    # Генерируем уникальное имя
                    unique_filename = generate_unique_filename(video_file.filename)
                    file_path = os.path.join(video_upload_path, unique_filename)

                    # Сохраняем файл
                    video_file.save(file_path)

                    # Создаем запись в базе
                    part_video = PartVideo(
                        part_id=part.id,
                        filename=unique_filename,
                        original_filename=video_file.filename
                    )
                    db.session.add(part_video)

        db.session.commit()
        return redirect(f'/parts/{part.id}')

    except Exception as e:
        db.session.rollback()
        # Если произошла ошибка, удаляем созданную папку
        if 'part' in locals():
            from app.utils.file_handling import delete_part_folder
            delete_part_folder(part.id)
        return f"Ошибка при добавлении детали: {str(e)}", 400

@parts_bp.route("/parts/<int:pid>/edit", methods=["GET", "POST"], strict_slashes=False)
@admin_required
def edit_part(pid):
    part = Part.query.get_or_404(pid)

    if request.method == "POST":
        try:
            # Обновляем основные данные
            part.name = request.form['name']
            part.car = request.form["car"]
            part.part_number = request.form['part_number']
            part.description = request.form['description']
            part.price_in = int(request.form['price_in'])
            part.price_out = int(request.form['price_out'])
            part.quantity = int(request.form['quantity'])  # ← Обновляем количество

            # Получаем пути к папкам детали
            part_upload_path = get_upload_path(part.id)
            video_upload_path = get_video_upload_path(part.id)

            # Обработка УДАЛЕНИЯ изображений
            if 'delete_images' in request.form:
                delete_ids = request.form.getlist('delete_images')
                for image_id in delete_ids:
                    image = PartImage.query.get(int(image_id))
                    if image and image.part_id == part.id:
                        # Удаляем файл с диска
                        delete_image_file(part.id, image.filename)
                        # Удаляем запись из БД
                        db.session.delete(image)

            # Обработка УДАЛЕНИЯ видео
            if 'delete_videos' in request.form:
                delete_ids = request.form.getlist('delete_videos')
                for video_id in delete_ids:
                    video = PartVideo.query.get(int(video_id))
                    if video and video.part_id == part.id:
                        # Удаляем файл с диска
                        delete_video_file(part.id, video.filename)
                        # Удаляем запись из БД
                        db.session.delete(video)

            # Обработка установки главного изображения
            if 'main_image' in request.form:
                main_image_id = int(request.form['main_image'])
                # Сбрасываем все is_main на False
                for image in part.images:
                    image.is_main = False
                # Устанавливаем выбранное как главное
                main_image = PartImage.query.get(main_image_id)
                if main_image and main_image.part_id == part.id:
                    main_image.is_main = True

            # Обработка НОВЫХ изображений
            if 'images' in request.files:
                files = request.files.getlist('images')

                for i, image_file in enumerate(files):
                    if image_file and image_file.filename != '' and allowed_file(image_file.filename):
                        # Проверяем размер файла
                        image_file.seek(0, 2)
                        file_size = image_file.tell()
                        image_file.seek(0)

                        if file_size > current_app.config['MAX_FILE_SIZE']:
                            continue

                        # Генерируем уникальное имя
                        unique_filename = generate_unique_filename(image_file.filename)
                        file_path = os.path.join(part_upload_path, unique_filename)

                        # Сохраняем файл
                        image_file.save(file_path)

                        # Создаем запись в базе
                        part_image = PartImage(
                            part_id=part.id,
                            filename=unique_filename,
                            is_main=(i == 0 and not part.images)  # Главное, если первое и нет других изображений
                        )
                        db.session.add(part_image)

            # Обработка НОВЫХ видео
            if 'videos' in request.files:
                video_files = request.files.getlist('videos')

                for video_file in video_files:
                    if video_file and video_file.filename != '' and allowed_video(video_file.filename):
                        # Проверяем размер файла
                        video_file.seek(0, 2)
                        file_size = video_file.tell()
                        video_file.seek(0)

                        if file_size > current_app.config['MAX_VIDEO_SIZE']:
                            continue

                        # Генерируем уникальное имя
                        unique_filename = generate_unique_filename(video_file.filename)
                        file_path = os.path.join(video_upload_path, unique_filename)

                        # Сохраняем файл
                        video_file.save(file_path)

                        # Создаем запись в базе
                        part_video = PartVideo(
                            part_id=part.id,
                            filename=unique_filename,
                            original_filename=video_file.filename
                        )
                        db.session.add(part_video)

            db.session.commit()
            return redirect(f"/parts/{pid}")

        except Exception as e:
            db.session.rollback()
            return f"Ошибка при обновлении: {str(e)}", 400

    return render_template('edit_part.html', part=part)

@parts_bp.route("/search", methods=["GET"], strict_slashes=False)
def search():
    search_request = request.args.get("q")

    if not search_request:
        return render_template("index.html")

    try:
        conditions = []

        if search_request.isdigit():
            conditions.append(Part.id == int(search_request))

        search_pattern = f"%{search_request}%"
        conditions.extend([
            Part.name.ilike(search_pattern),
            Part.car.ilike(search_pattern),
            Part.part_number.ilike(search_pattern),
            Part.description.ilike(search_pattern)
        ])

        parts = Part.query.filter(or_(*conditions)).all()

        return render_template(
            "all_parts.html",
            parts=parts
        )

    except Exception as e:
        return f"Ошибка при поиске: {str(e)}", 500