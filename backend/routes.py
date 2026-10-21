from datetime import date, datetime, timedelta, timezone
from functools import wraps
from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import or_
from backend.models import Book, BookIssue, User, db

api = Blueprint("api", __name__)
def body(): return request.get_json(silent=True) or {}
def auth(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            raw_id = request.headers.get("X-User-Id")
            user = db.session.get(User, int(raw_id)) if raw_id and raw_id.isdigit() else None
            if not user or (role and user.role != role): return jsonify({"error": "Authentication or permission required"}), 401
            g.user = user
            return fn(*args, **kwargs)
        return wrapped
    return decorator

@api.post("/auth/register")
def register():
    data = body(); name = data.get("name", "").strip(); email = data.get("email", "").strip().lower(); password = data.get("password", "")
    if not name or not email or len(password) < 8: return jsonify({"error": "Name, email, and an 8-character password are required"}), 400
    if User.query.filter_by(email=email).first(): return jsonify({"error": "Email is already registered"}), 409
    user = User(name=name, email=email, role="student"); user.set_password(password); db.session.add(user); db.session.commit()
    return jsonify({"user": user.public()}), 201

@api.post("/auth/login")
def login():
    data = body(); user = User.query.filter_by(email=data.get("email", "").strip().lower()).first()
    if not user or not user.check_password(data.get("password", "")): return jsonify({"error": "Invalid email or password"}), 401
    return jsonify({"user": user.public(), "user_id": user.id})

@api.get("/books")
def books():
    q = request.args.get("q", "").strip()
    query = Book.query.filter(or_(Book.title.ilike(f"%{q}%"), Book.author.ilike(f"%{q}%"), Book.isbn.ilike(f"%{q}%"))) if q else Book.query
    return jsonify({"books": [book.public() for book in query.order_by(Book.title).all()]})

@api.post("/books")
@auth("admin")
def add_book():
    data = body()
    try: copies = int(data.get("total_copies", 1))
    except (TypeError, ValueError): copies = 0
    if copies < 1 or not data.get("title") or not data.get("author"): return jsonify({"error": "Title, author, and copies are required"}), 400
    book = Book(title=data["title"].strip(), author=data["author"].strip(), isbn=data.get("isbn") or None, total_copies=copies, available_copies=copies)
    db.session.add(book); db.session.commit(); return jsonify({"book": book.public()}), 201

@api.post("/issues")
@auth()
def issue():
    data = body(); book = db.session.get(Book, data.get("book_id"))
    try: student_id = int(data.get("student_id", g.user.id))
    except (TypeError, ValueError): return jsonify({"error": "Invalid student id"}), 400
    student = db.session.get(User, student_id)
    if g.user.role != "admin" and student_id != g.user.id: return jsonify({"error": "Admin permission required"}), 403
    if not book or not student or book.available_copies < 1: return jsonify({"error": "Book unavailable or student not found"}), 400
    if BookIssue.query.filter_by(book_id=book.id, student_id=student.id, returned_at=None).first(): return jsonify({"error": "Book already issued to this student"}), 409
    item = BookIssue(book=book, student=student, due_date=date.today() + timedelta(days=current_app.config["LOAN_DAYS"])); book.available_copies -= 1; db.session.add(item); db.session.commit()
    return jsonify({"issue": item.public()}), 201

@api.get("/issues")
@auth()
def issues():
    query = BookIssue.query if g.user.role == "admin" else BookIssue.query.filter_by(student_id=g.user.id)
    return jsonify({"issues": [item.public() for item in query.order_by(BookIssue.due_date.desc()).all()]})

@api.post("/issues/<int:issue_id>/return")
@auth()
def return_book(issue_id):
    item = db.session.get(BookIssue, issue_id)
    if not item or item.returned_at or (g.user.role != "admin" and item.student_id != g.user.id): return jsonify({"error": "Issue not found or already returned"}), 404
    late_days = max(0, (date.today() - item.due_date).days); item.fine_amount = round(late_days * current_app.config["FINE_PER_DAY"], 2); item.returned_at = datetime.now(timezone.utc); item.book.available_copies += 1; db.session.commit()
    return jsonify({"issue": item.public(), "fine_amount": float(item.fine_amount)})

@api.get("/students")
@auth("admin")
def students(): return jsonify({"students": [u.public() for u in User.query.filter_by(role="student").order_by(User.name).all()]})
