from flask import Flask


def create_app(config_class='app.config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.url_map.strict_slashes = False

    # Initialize extensions
    from .extensions import db
    db.init_app(app)

    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.parts import parts_bp
    from app.routes.sales import sales_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(parts_bp)
    app.register_blueprint(sales_bp)

    # Create admin user
    with app.app_context():
        db.create_all()
        from .utils.security import create_admin_user
        create_admin_user()

    return app


