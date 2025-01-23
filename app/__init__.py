from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin
from flask_migrate import Migrate
import os
import logging

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    # Enable CORS globally
    # CORS(
    #     app,
    #     resources={
    #         r"/api/*": {"origins": os.getenv("FRONTEND_URL", "http://localhost:5173")},
    #     },
    #     supports_credentials=True,
    # )
    CORS(
        app,
        resources={
            r"/api/*": {"origins": "*"},  # Allow all origins for routes starting with /api/
        },
        supports_credentials=True,
    )

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Logs to the console
    )
    app.logger.info("Logging is configured.")

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
    from .routes.available_models_routes import model_bp

    app.register_blueprint(deploy_bp, url_prefix="/api/deploy")
    app.register_blueprint(model_bp, url_prefix="/api/models")

    return app
