# src/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER', 'iotta')}:"
    f"{os.getenv('DB_PASSWORD', 'iotta')}@"
    f"db:5432/"
    f"{os.getenv('DB_NAME', 'iotta')}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()