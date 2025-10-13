from flask import Flask, render_template, request, redirect, current_app, jsonify, session
from utils import allowed_file, get_upload_path, generate_unique_filename, MAX_FILES, MAX_FILE_SIZE
from werkzeug.utils import secure_filename
from functools import wraps
from security import password_hasher
import argon2
import os
import jwt
import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import or_

from models import User, Part, PartImage, db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///updb.db"
app.config["SECRET_KEY"] = "TEST_KEY_SECRET_EXAMPLE"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(minutes=60)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = datetime.timedelta(weeks=2)


# Декоратор для проверки авторизации и прав admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            # Проверяем сессию для веб-запросов
            if 'user_id' not in session:
                return redirect('/login')

            user = User.query.get(session['user_id'])
            if not user or user.login != 'admin':
                return redirect('/login')

            return f(*args, **kwargs)

        # Проверяем JWT токен для API запросов
        try:
            if token.startswith('Bearer '):
                token = token[7:]

            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user = User.query.get(payload['user_id'])

            if not user or user.login != 'admin':
                return jsonify({'error': 'Admin access required'}), 403

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)

    return decorated_function


def create_access_token(user_id):
    expires = datetime.datetime.utcnow() + app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    token = jwt.encode({
        'user_id': user_id,
        'exp': expires,
        'type': 'access'
    }, app.config['SECRET_KEY'], algorithm='HS256')
    return token


def create_refresh_token(user_id):
    expires = datetime.datetime.utcnow() + app.config["JWT_REFRESH_TOKEN_EXPIRES"]
    token = jwt.encode({
        'user_id': user_id,
        'exp': expires,
        'type': 'refresh'
    }, app.config['SECRET_KEY'], algorithm='HS256')
    return token


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            username = request.form.get("username")
            password = request.form.get("password")

            user = User.query.filter_by(login=username).first()

            if user and password_hasher.verify_password(user.password, password):
                # Сессия для браузера
                session['user_id'] = user.id
                session['username'] = user.login

                # JWT для API
                access_token = create_access_token(user.id)
                refresh_token = create_refresh_token(user.id)

                if request.headers.get('Content-Type') == 'application/json':
                    return jsonify({
                        'access_token': access_token,
                        'refresh_token': refresh_token,
                        'user': user.login
                    })

                return redirect('/')
            else:
                error = "Неверный логин или пароль"
                if request.headers.get('Content-Type') == 'application/json':
                    return jsonify({'error': error}), 401
                return render_template("login.html", error=error)

        except Exception as e:
            error = f"Ошибка авторизации: {str(e)}"
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({'error': error}), 500
            return render_template("login.html", error=error)

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect('/login')


@app.route("/refresh", methods=["POST"])
def refresh_token():
    try:
        refresh_token = request.json.get('refresh_token')
        if not refresh_token:
            return jsonify({'error': 'Refresh token required'}), 400

        payload = jwt.decode(refresh_token, app.config['SECRET_KEY'], algorithms=['HS256'])

        if payload.get('type') != 'refresh':
            return jsonify({'error': 'Invalid token type'}), 401

        user = User.query.get(payload['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 401

        new_access_token = create_access_token(user.id)
        return jsonify({'access_token': new_access_token})

    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Refresh token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid refresh token'}), 401


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/parts", methods=["GET"])
def all_parts():
    parts = Part.query.options(db.joinedload(Part.images)).all()
    return render_template("all_parts.html", parts=parts)



@app.route("/parts/new_part", methods=["GET"])
@admin_required
def new_part_form():
    return render_template("new_part.html")


@app.route("/parts/<int:pid>", methods=["GET"])
def get_one_part(pid):
    try:
        part = db.session.get(Part, pid)
        return render_template("part.html", part=part)
    except Exception as e:
        return f"Деталь не найдена - {e}"


@app.route("/parts/<int:pid>", methods=["DELETE"])
@admin_required
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
@admin_required
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
@admin_required
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
                    # Удаленик старое изображение если есть
                    if part.image_filename:
                        old_image_path = os.path.join(get_upload_path(), part.image_filename)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)

                    # Сохранение нового изображения
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


@app.route("/search", methods=["GET"])
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



def create_admin_user():
    with app.app_context():
        admin = User.query.filter_by(login='admin').first()
        if not admin:
            password_hash = password_hasher.hash_password("!Fdvj23mn@i")
            admin = User(
                login='admin',
                password=password_hash
            )
            db.session.add(admin)
            db.session.commit()




if __name__ == "__main__":
    db.init_app(app)
    with app.app_context():
        db.create_all()
        create_admin_user()
    app.run()