from flask import Flask, render_template, request, redirect, current_app
from utils import allowed_file, get_upload_path, generate_unique_filename, MAX_FILES, MAX_FILE_SIZE
from werkzeug.utils import secure_filename
import os

from models import User, Part, PartImage, db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///updb.db"


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/parts", methods=["GET"])
def all_parts():
    parts = Part.query.options(db.joinedload(Part.images)).all()
    return render_template("all_parts.html" , parts=parts)

@app.route("/parts/<int:pid>")
def part_detail(pid):
    part = Part.query.options(db.joinedload(Part.images)).get_or_404(pid)
    return render_template("part.html", part=part)



@app.route("/parts/new_part", methods=["GET"])
def new_part_form():
    return render_template("new_part.html")

@app.route("/parts/<int:pid>", methods=["GET"])
def get_one_part(pid):
    try:
        part = db.session.get(Part, pid)
        return render_template("part.html", part=part)
    except Exception as e:
        return f"error - {e}"


@app.route("/parts/<int:pid>", methods=["DELETE"])
def delete_one_part(pid):
    try:
        to_delete = db.session.get(Part, pid)

        if not to_delete:
            return "Part not found", 404

        # Удаляем файлы изображений с диска
        for image in to_delete.images:
            image_path = os.path.join(
                current_app.root_path,
                'static/uploads/parts',
                image.filename
            )
            if os.path.exists(image_path):
                os.remove(image_path)

        # Удаляем деталь (изображения удалятся автоматически благодаря каскаду)
        db.session.delete(to_delete)
        db.session.commit()

        return "deleted", 200

    except Exception as e:
        db.session.rollback()
        return f"error - {e}", 500


@app.route("/parts/new_part/added", methods=["POST"])
def add_part():
    try:
        # Проверяем количество файлов
        if "images" in request.files:
            files = request.files.getlist("images")
            if len(files) > MAX_FILES:
                return f"Слишком много файлов. Максимум: {MAX_FILES}", 400

        # Обработка текстовых данных
        name = request.form["name"]
        car = request.form["car"]
        part_number = request.form["part_number"]
        description = request.form["description"]
        price_in = int(request.form["price_in"])
        price_out = int(request.form["price_out"])

        # Создаем деталь
        part = Part(
            name=name,
            car=car,
            part_number=part_number,
            description=description,
            price_in=price_in,
            price_out=price_out
        )

        db.session.add(part)
        db.session.flush()  # Получаем ID до коммита

        # Обработка изображений
        if 'images' in request.files:
            files = request.files.getlist('images')
            upload_path = get_upload_path()

            for i, image_file in enumerate(files):
                if image_file and image_file.filename != '' and allowed_file(image_file.filename):
                    # Проверяем размер файла
                    image_file.seek(0, 2)  # Перемещаемся в конец файла
                    file_size = image_file.tell()
                    image_file.seek(0)  # Возвращаемся в начало

                    if file_size > MAX_FILE_SIZE:
                        continue  # Пропускаем слишком большие файлы

                    # Генерируем уникальное имя
                    unique_filename = generate_unique_filename(image_file.filename)
                    file_path = os.path.join(upload_path, unique_filename)

                    # Сохраняем файл
                    image_file.save(file_path)

                    # Создаем запись в базе
                    part_image = PartImage(
                        part_id=part.id,
                        filename=unique_filename,
                        is_main=(i == 0)  # Первое фото - главное
                    )
                    db.session.add(part_image)

        db.session.commit()
        return redirect('/parts')

    except Exception as e:
        db.session.rollback()
        return f"Ошибка при добавлении детали: {str(e)}", 400


@app.route("/parts/<int:pid>/edit", methods=["GET", "POST"])
def edit_part(pid):
    part = Part.query.get_or_404(pid)

    if request.method == "POST":
        try:
            part.name = request.form['name']
            part.car = request.form["car"]
            part.part_number = request.form['part_number']
            part.description = request.form['description']
            part.price_in = int(request.form['price_in'])
            part.price_out = int(request.form['price_out'])

            # Обработка нового изображения
            if 'image' in request.files:
                image_file = request.files['image']
                if image_file and image_file.filename != '' and allowed_file(image_file.filename):
                    # Удаляем старое изображение если есть
                    if part.image_filename:
                        old_image_path = os.path.join(get_upload_path(), part.image_filename)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)

                    # Сохраняем новое
                    filename = secure_filename(image_file.filename)
                    unique_filename = f"{part.part_number}_{filename}"
                    upload_path = get_upload_path()
                    image_file.save(os.path.join(upload_path, unique_filename))
                    part.image_filename = unique_filename

            db.session.commit()
            return redirect(f"/parts/{pid}")
        except Exception as e:
            return f"Ошибка при обновлении: {str(e)}", 400

    return render_template('edit_part.html', part=part)


if __name__ == "__main__":
    # with app.app_context():
    #     db.init_app(app)
    #     db.create_all()
    db.init_app(app)
    app.run()