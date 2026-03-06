import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, JSON
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(Text, nullable=True)
    github_id = Column(String, unique=True, nullable=True)
    github_username = Column(String, unique=True, nullable=True)
    github_token = Column(Text, nullable=True)
    openai_key = Column(Text, nullable=True)
    anthropic_key = Column(Text, nullable=True)
    gemini_key = Column(Text, nullable=True)
    cerebras_key = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RepoStatus(Base):
    __tablename__ = "repo_status"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    repo_full_name = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, indexing, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    total_files = Column(Integer, default=0)
    indexed_files = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    repo_full_name = Column(String, nullable=False)
    messages = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
