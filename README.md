# Library Management System

Deployment-ready Flask + PostgreSQL (Neon) library system. Admins add books and issue/return them; students search, issue, and view their books. Late returns calculate a configurable daily fine.

## Setup

1. Create a Neon PostgreSQL database and run `database/schema.sql`.
2. Copy `.env.example` to `.env`, setting `DATABASE_URL` and `SECRET_KEY`.
3. From the project root, install `backend/requirements.txt` and run `flask --app backend.app run` with the project root on `PYTHONPATH`.

The API is under `/api`; the Flask service also serves the frontend. The first registered user is a student. Promote an administrator in Neon with `UPDATE users SET role = 'admin' WHERE email = '...';`.

Use the included `render.yaml` for Render. Set `DATABASE_URL` to the Neon pooled connection string and `CORS_ORIGINS` to the frontend URL. Passwords are hashed with Werkzeug. SQLite is not supported or used.
