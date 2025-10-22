import argon2
import jwt
import datetime
from flask import current_app
from functools import wraps
from flask import request, session, jsonify, redirect


class PasswordHasher:
    def __init__(self):
        self.hasher = argon2.PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=1,
            hash_len=32,
            salt_len=16
        )

    def hash_password(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify_password(self, hashed_password: str, password: str) -> bool:
        try:
            return self.hasher.verify(hashed_password, password)
        except (argon2.exceptions.VerifyMismatchError,
                argon2.exceptions.VerificationError,
                argon2.exceptions.InvalidHashError):
            return False


def create_access_token(user_id):
    expires = datetime.datetime.utcnow() + current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    token = jwt.encode({
        'user_id': user_id,
        'exp': expires,
        'type': 'access'
    }, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token


def create_refresh_token(user_id):
    expires = datetime.datetime.utcnow() + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]
    token = jwt.encode({
        'user_id': user_id,
        'exp': expires,
        'type': 'refresh'
    }, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.models import User  # Локальный импорт чтобы избежать циклической зависимости

        token = request.headers.get('Authorization')

        if not token:
            # Check session for web requests
            if 'user_id' not in session:
                return redirect('/login')

            user = User.query.get(session['user_id'])
            if not user or user.login != 'admin':
                return redirect('/login')

            return f(*args, **kwargs)

        # Check JWT token for API requests
        try:
            if token.startswith('Bearer '):
                token = token[7:]

            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user = User.query.get(payload['user_id'])

            if not user or user.login != 'admin':
                return jsonify({'error': 'Admin access required'}), 403

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)

    return decorated_function


def create_admin_user():
    from app.extensions import db
    from app.models import User

    admin = User.query.filter_by(login='admin').first()
    if not admin:
        password_hasher = PasswordHasher()
        password_hash = password_hasher.hash_password("12345")
        admin = User(
            login='admin',
            password=password_hash
        )
        db.session.add(admin)
        db.session.commit()