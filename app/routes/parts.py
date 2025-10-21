from flask import Blueprint, render_template, request, redirect, current_app, jsonify, session
from app.extensions import db
from app.models import Part, PartImage
from app.utils.security import admin_required
from app.utils.file_handling import allowed_file, get_upload_path, generate_unique_filename
from sqlalchemy import or_
import os

parts_bp = Blueprint('parts', __name__)

@parts_bp.route("/parts", methods=["GET"])
def all_parts():
    parts = Part.query.options(db.joinedload(Part.images)).all()
    return render_template("all_parts.html", parts=parts)

@parts_bp.route("/parts/new_part", methods=["GET"])
@admin_required
def new_part_form():
    return render_template("new_part.html")

@parts_bp.route("/parts/<int:pid>", methods=["GET"])
def get_one_part(pid):
    try:
        part = db.session.get(Part, pid)
        return render_template("part.html", part=part)
    except Exception as e:
        return f"Деталь не найдена - {e}"

@parts_bp.route("/parts/<int:pid>", methods=["DELETE"])
@admin_required
def delete_one_part(pid):
    try:
        to_delete = db.session.get(Part, pid)

        if not to_delete:
            return "Part not found", 404

        # Delete image files from disk
        for image in to_delete.images:
            image_path = os.path.join(
                current_app.root_path,
                'static/uploads/parts',
                image.filename
            )
            if os.path.exists(image_path):
                os.remove(image_path)

        # Delete part (images will be deleted automatically due to cascade)
        db.session.delete(to_delete)
        db.session.commit()

        return "deleted", 200

    except Exception as e:
        db.session.rollback()
        return f"error - {e}", 500

@parts_bp.route("/parts/new_part/added", methods=["POST"])
@admin_required
def add_part():
    try:
        # Check number of files
        if "images" in request.files:
            files = request.files.getlist("images")
            if len(files) > current_app.config['MAX_FILES']:
                return f"Слишком много файлов. Максимум: {current_app.config['MAX_FILES']}", 400

        # Process text data
        name = request.form["name"]
        car = request.form["car"]
        part_number = request.form["part_number"]
        description = request.form["description"]
        price_in = int(request.form["price_in"])
        price_out = int(request.form["price_out"])

        # Create part
        part = Part(
            name=name,
            car=car,
            part_number=part_number,
            description=description,
            price_in=price_in,
            price_out=price_out
        )

        db.session.add(part)
        db.session.flush()  # Get ID before commit

        # Process images
        if 'images' in request.files:
            files = request.files.getlist('images')
            upload_path = get_upload_path()

            for i, image_file in enumerate(files):
                if image_file and image_file.filename != '' and allowed_file(image_file.filename):
                    # Check file size
                    image_file.seek(0, 2)  # Move to end of file
                    file_size = image_file.tell()
                    image_file.seek(0)  # Return to beginning

                    if file_size > current_app.config['MAX_FILE_SIZE']:
                        continue  # Skip files that are too large

                    # Generate unique name
                    unique_filename = generate_unique_filename(image_file.filename)
                    file_path = os.path.join(upload_path, unique_filename)

                    # Save file
                    image_file.save(file_path)

                    # Create database record
                    part_image = PartImage(
                        part_id=part.id,
                        filename=unique_filename,
                        is_main=(i == 0)  # First photo is main
                    )
                    db.session.add(part_image)

        db.session.commit()
        return redirect('/parts')

    except Exception as e:
        db.session.rollback()
        return f"Ошибка при добавлении детали: {str(e)}", 400


@parts_bp.route("/parts/<int:pid>/edit", methods=["GET", "POST"])
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

            # Обработка новых изображений
            if 'images' in request.files:
                files = request.files.getlist('images')
                upload_path = get_upload_path()

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
                        file_path = os.path.join(upload_path, unique_filename)

                        # Сохраняем файл
                        image_file.save(file_path)

                        # Создаем запись в базе
                        part_image = PartImage(
                            part_id=part.id,
                            filename=unique_filename,
                            is_main=(i == 0 and not part.images)  # Главное, если первое и нет других изображений
                        )
                        db.session.add(part_image)

            # Обработка удаления изображений
            if 'delete_images' in request.form:
                delete_ids = request.form.getlist('delete_images')
                for image_id in delete_ids:
                    image = PartImage.query.get(int(image_id))
                    if image and image.part_id == part.id:
                        # Удаляем файл с диска
                        image_path = os.path.join(upload_path, image.filename)
                        if os.path.exists(image_path):
                            os.remove(image_path)
                        # Удаляем запись из БД
                        db.session.delete(image)

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

            db.session.commit()
            return redirect(f"/parts/{pid}")

        except Exception as e:
            db.session.rollback()
            return f"Ошибка при обновлении: {str(e)}", 400

    return render_template('edit_part.html', part=part)


@parts_bp.route("/search", methods=["GET"])
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