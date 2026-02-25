from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from datetime import datetime
from db import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    platform = Column(String, nullable=False)
    platform_user_id = Column(String, unique=True, nullable=False)

    # Conversation control
    state = Column(String, default="NEW")

    # 🧠 Health conversation memory
    condition = Column(String, nullable=True)
    preferred_date = Column(String, nullable=True)
    preferred_time = Column(String, nullable=True)

    last_seen = Column(DateTime, default=datetime.utcnow)

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    condition = Column(String, nullable=True)
    preferred_date = Column(String, nullable=True)
    preferred_time = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String)  # "user" or "assistant"
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
