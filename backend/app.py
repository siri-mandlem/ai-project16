import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from backend.config import Config
from backend.models import db
from backend.routes import api


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


def create_app():
    app = Flask(
        __name__,
        static_folder=str(FRONTEND_DIR),
        static_url_path=""
    )

    # Load application configuration
    app.config.from_object(Config)

    # Validate required environment variables
    if not app.config.get("DATABASE_URL"):
        raise RuntimeError(
            "DATABASE_URL must be configured for Neon PostgreSQL."
        )

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY must be configured before starting the application."
        )

    # Configure the PostgreSQL connection URL
    database_url = app.config["DATABASE_URL"].strip()

    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://", "postgresql://", 1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize SQLAlchemy
    db.init_app(app)

    # Automatically create missing tables from imported models
    with app.app_context():
        db.create_all()

    # Configure CORS for API endpoints
    origins = app.config.get("CORS_ORIGINS", "*")
    allowed_origins = (
        [origin.strip() for origin in origins.split(",") if origin.strip()]
        if origins != "*"
        else "*"
    )

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins
            }
        }
    )

    # Register API routes
    app.register_blueprint(api, url_prefix="/api")

    # Health check for Render
    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    # Serve the frontend homepage
    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    # Serve frontend assets and support client-side routes
    @app.get("/<path:path>")
    def serve_frontend(path):
        requested_file = FRONTEND_DIR / path

        if requested_file.is_file():
            return send_from_directory(FRONTEND_DIR, path)

        # Do not return index.html for unknown API endpoints
        if path == "api" or path.startswith("api/"):
            return jsonify({"error": "API endpoint not found"}), 404

        return send_from_directory(FRONTEND_DIR, "index.html")

    # Handle HTTP errors without exposing internal details
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"error": error.description}), error.code

    # Handle unexpected application errors
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unhandled application error")
        return jsonify({"error": "Internal server error"}), 500

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)