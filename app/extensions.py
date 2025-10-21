from flask_sqlalchemy import SQLAlchemy
from .utils.security import PasswordHasher

db = SQLAlchemy()
password_hasher = PasswordHasher()