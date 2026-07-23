# app/models.py
from sqlalchemy import Column, Integer, String, Float, JSON, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    cards = relationship("Card", back_populates="owner", cascade="all, delete-orphan")

class Card(Base):
    __tablename__ = "cards"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    variant = Column(String(50), nullable=True)
    collection_name = Column(String(100), nullable=True)
    number = Column(String(20), nullable=True)
    collection_number = Column(String(20), nullable=True)
    picture_path = Column(String(255), nullable=True)
    quantity = Column(Integer, default=1)
    value = Column(Float, default=0.0)
    extra_data = Column(JSON, default={})
    
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner = relationship("User", back_populates="cards")