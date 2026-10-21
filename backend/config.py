
import os
from pathlib import Path
from dotenv import load_dotenv

# Project root directory (parent of backend/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from the project root .env file
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    FINE_PER_DAY = float(os.getenv("FINE_PER_DAY", "2.00"))
    LOAN_DAYS = int(os.getenv("LOAN_DAYS", "14"))

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")