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
    state = Column(String, default="NEW")
    last_seen = Column(DateTime, default=datetime.utcnow)

    # ── Real Estate Qualification Fields ──
    client_name = Column(String, nullable=True)
    intent = Column(String, nullable=True)      # "buy" or "rent"
    budget = Column(String, nullable=True)
    bedrooms = Column(String, nullable=True)
    preferred_location = Column(String, nullable=True)
    viewing_date = Column(String, nullable=True)
    viewing_time = Column(String, nullable=True)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    client_name = Column(String, nullable=True)
    property_interest = Column(String, nullable=True)
    viewing_date = Column(String, nullable=True)
    viewing_time = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")