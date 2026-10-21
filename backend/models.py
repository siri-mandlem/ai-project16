from datetime import date, datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    issues = db.relationship("BookIssue", back_populates="student", lazy=True)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)
    def public(self): return {"id": self.id, "name": self.name, "email": self.email, "role": self.role}

class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    author = db.Column(db.String(255), nullable=False, index=True)
    isbn = db.Column(db.String(32), unique=True, nullable=True)
    total_copies = db.Column(db.Integer, nullable=False, default=1)
    available_copies = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    issues = db.relationship("BookIssue", back_populates="book", lazy=True)
    def public(self): return {"id": self.id, "title": self.title, "author": self.author, "isbn": self.isbn, "total_copies": self.total_copies, "available_copies": self.available_copies}

class BookIssue(db.Model):
    __tablename__ = "book_issues"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    issued_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    due_date = db.Column(db.Date, nullable=False)
    returned_at = db.Column(db.DateTime(timezone=True), nullable=True)
    fine_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    student = db.relationship("User", back_populates="issues")
    book = db.relationship("Book", back_populates="issues")
    def public(self):
        end_date = self.returned_at.date() if self.returned_at else date.today()
        return {"id": self.id, "student": self.student.public(), "book": self.book.public(), "issued_at": self.issued_at.isoformat(), "due_date": self.due_date.isoformat(), "returned_at": self.returned_at.isoformat() if self.returned_at else None, "fine_amount": float(self.fine_amount), "late_days": max(0, (end_date - self.due_date).days), "status": "returned" if self.returned_at else "issued"}
