# app/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from fastapi import HTTPException

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://gradeuser:gradepass@localhost:5432/gradeinsight")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_tenant_from_host(host: str) -> str:
    if not host:
        raise HTTPException(status_code=400, detail="Missing Host header")
    subdomain = host.split(".")[0].lower()
    if not subdomain:
        raise HTTPException(status_code=400, detail="Invalid tenant in host")
    return subdomain
