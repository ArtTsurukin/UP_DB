from flask import Blueprint, request, render_template, redirect, session, jsonify, current_app
from app.extensions import db, password_hasher
from app.models import User
from app.utils.security import create_access_token, create_refresh_token
import jwt

auth_bp = Blueprint("auth", __name__)

# Используем url_prefix при регистрации blueprint
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            username = request.form.get("username")
            password = request.form.get("password")

            user = User.query.filter_by(login=username).first()

            if user and password_hasher.verify_password(user.password, password):
                # Session for browser
                session['user_id'] = user.id
                session['username'] = user.login

                # JWT for API
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

@auth_bp.route("/logout", endpoint='logout')
def logout():
    session.clear()
    return redirect('/login')

@auth_bp.route("/refresh", methods=["POST"], endpoint='refresh')
def refresh():
    try:
        refresh_token = request.json.get('refresh_token')
        if not refresh_token:
            return jsonify({'error': 'Refresh token required'}), 400

        payload = jwt.decode(refresh_token, current_app.config['SECRET_KEY'], algorithms=['HS256'])

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