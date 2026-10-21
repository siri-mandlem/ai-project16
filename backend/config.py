import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DATABASE_URL = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FINE_PER_DAY = float(os.environ.get("FINE_PER_DAY", "2.00"))
    LOAN_DAYS = int(os.environ.get("LOAN_DAYS", "14"))
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
