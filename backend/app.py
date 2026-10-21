import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import inspect, text
from werkzeug.exceptions import HTTPException

from backend.config import Config
from backend.models import db, User, Book, BookIssue
from backend.routes import api


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


def create_app():
    app = Flask(
        __name__,
        static_folder=str(FRONTEND_DIR),
        static_url_path=""
    )

    app.config.from_object(Config)

    if not app.config.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is missing.")

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is missing.")

    database_url = app.config["DATABASE_URL"].strip()

    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://", "postgresql://", 1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Create tables in the configured Neon database.
    with app.app_context():
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        db.create_all()

        tables = inspect(db.engine).get_table_names()
        app.logger.info("Connected to database successfully.")
        app.logger.info("Database tables: %s", tables)

    origins = app.config.get("CORS_ORIGINS", "*")
    allowed_origins = (
        [item.strip() for item in origins.split(",") if item.strip()]
        if origins != "*"
        else "*"
    )

    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}}
    )

    app.register_blueprint(api, url_prefix="/api")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:path>")
    def serve_frontend(path):
        requested_file = FRONTEND_DIR / path

        if requested_file.is_file():
            return send_from_directory(FRONTEND_DIR, path)

        if path == "api" or path.startswith("api/"):
            return jsonify({"error": "API endpoint not found"}), 404

        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"error": error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unhandled application error")
        return jsonify({"error": "Internal server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)