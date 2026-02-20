from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, JSON
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    github_username = Column(String, unique=True, nullable=False)
    github_token = Column(Text, nullable=False)
    openai_key = Column(Text, nullable=True)
    anthropic_key = Column(Text, nullable=True)
    gemini_key = Column(Text, nullable=True)
    cerebras_key = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    repo_full_name = Column(String, nullable=False)
    messages = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
