from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    # Enable CORS globally
    CORS(
        app,
        resources={
            r"/api/*": {"origins": os.getenv("FRONTEND_URL", "http://localhost:5173")},
        },
        supports_credentials=True,
    )

    # PostgreSQL configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "postgresql://flaskuser:flaskpassword@localhost:5432/flaskdb"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register Blueprints
    from .routes.container_routes import deploy_bp

    app.register_blueprint(deploy_bp, url_prefix="/api/deploy")

    return app
