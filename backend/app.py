
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

# Load .env before importing Config.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from backend.config import Config
from backend.models import db, User, Book, BookIssue
from backend.routes import api

FRONTEND_ROOT = PROJECT_ROOT / "frontend"

logger = logging.getLogger(__name__)


def get_database_url():
    """Validate and normalize the Neon PostgreSQL connection URL."""
    database_url = os.environ.get("DATABASE_URL", "").strip()

    if not database_url:
        database_url = (getattr(Config, "DATABASE_URL", None) or "").strip()

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Configure your Neon PostgreSQL URL "
            "in .env or Render environment variables."
        )

    
    url = make_url(database_url)

    if url.drivername in ("postgres", "postgresql"):
        url = url.set(drivername="postgresql+psycopg")

    if url.drivername != "postgresql+psycopg":
        raise RuntimeError(
            "This application requires PostgreSQL. "
            "Check your DATABASE_URL."
        )

    if "sslmode" not in url.query:
        url = url.update_query_dict({"sslmode": "require"})

    return url.render_as_string(hide_password=False)


def migrate_legacy_books_schema(app):
    """Add and populate available_copies for databases created by older versions."""
    with db.engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE books "
                "ADD COLUMN IF NOT EXISTS available_copies INTEGER"
            )
        )
        result = connection.execute(
            text(
                """
                UPDATE books AS book
                SET available_copies = GREATEST(
                    book.total_copies - (
                        SELECT COUNT(*)
                        FROM book_issues AS issue
                        WHERE issue.book_id = book.id
                          AND issue.returned_at IS NULL
                    ),
                    0
                )
                WHERE book.available_copies IS NULL
                """
            )
        )
        connection.execute(
            text(
                "ALTER TABLE books "
                "ALTER COLUMN available_copies SET NOT NULL"
            )
        )

    if result.rowcount:
        app.logger.info(
            "Migrated available_copies for %s existing book(s).",
            result.rowcount,
        )



def initialize_database(app):
    """Connect to PostgreSQL, create missing tables, and verify them."""
    required_tables = {
        User.__tablename__,
        Book.__tablename__,
        BookIssue.__tablename__,
    }

    try:
        with app.app_context():
            # Verify that the configured PostgreSQL database is reachable.
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))

            app.logger.info("PostgreSQL connection successful.")

            # Create any tables missing from the database.
            db.create_all()

            # db.create_all() does not add columns to existing tables.
            migrate_legacy_books_schema(app)

            # Verify that the required tables exist.
            inspector = inspect(db.engine)
            existing_tables = set(inspector.get_table_names())
            missing_tables = required_tables - existing_tables

            if missing_tables:
                raise RuntimeError(
                    "Table creation incomplete. Missing tables: "
                    + ", ".join(sorted(missing_tables))
                )

            app.logger.info(
                "Database initialization successful. Tables found: %s",
                ", ".join(sorted(required_tables)),
            )

    except SQLAlchemyError as error:
        app.logger.exception(
            "PostgreSQL connection or table initialization failed."
        )
        raise RuntimeError(
            "Could not initialize the Neon PostgreSQL database. "
            "Check DATABASE_URL, database permissions, network access, "
            "and PostgreSQL driver installation."
        ) from error


def create_app(test_config=None):
    app = Flask(
        __name__,
        static_folder=str(FRONTEND_ROOT),
        static_url_path="",
    )

    app.config.from_object(Config)

    # Always use the validated PostgreSQL URL.
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
    }

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY is missing. Configure it in .env or Render."
        )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    # Models are imported above, so SQLAlchemy metadata knows about
    # users, books, and book_issues before create_all() runs.
    initialize_database(app)

    # Configure CORS.
    origins = app.config.get("CORS_ORIGINS", "*")

    if isinstance(origins, str):
        allowed_origins = (
            [origin.strip() for origin in origins.split(",")
             if origin.strip()]
            if origins.strip() != "*"
            else "*"
        )
    else:
        allowed_origins = origins

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins,
            }
        },
    )

    # Register the library API routes.
    app.register_blueprint(api, url_prefix="/api")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.get("/ready")
    def ready():
        try:
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))

            return jsonify({"status": "ready"}), 200

        except SQLAlchemyError:
            app.logger.exception("Database readiness check failed.")
            return jsonify({"status": "database unavailable"}), 503

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_ROOT, "index.html")

    @app.get("/<path:path>")
    def serve_frontend(path):
        requested_file = FRONTEND_ROOT / path

        if requested_file.is_file():
            return send_from_directory(FRONTEND_ROOT, path)

        # Unknown API endpoints must return 404, not index.html.
        if path == "api" or path.startswith("api/"):
            return jsonify({"error": "API endpoint not found"}), 404

        return send_from_directory(FRONTEND_ROOT, "index.html")

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"error": error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unhandled application error")

        if app.config.get("TESTING"):
            raise error

        return jsonify({"error": "Internal server error"}), 500

    return app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    port = int(os.environ.get("PORT", "5000"))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
