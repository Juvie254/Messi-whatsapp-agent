from datetime import datetime
from memory import get_or_create_user
from entity_extractor import extract_entities
from context_builder import build_system_prompt
from llm import call_llm
from messaging import send_whatsapp_message
from models import Booking, Message
from db import SessionLocal

BUSINESS_OWNER_PHONE = "254714638286"  # Replace with Peter's real number


def booking_ready(user):
    return (
        user.condition and
        user.preferred_date and
        user.preferred_time
    )


def create_booking(db, user):
    booking = Booking(
        user_id=user.id,
        condition=user.condition,
        preferred_date=user.preferred_date,
        preferred_time=user.preferred_time
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Clear structured booking fields after saving
    user.condition = None
    user.preferred_date = None
    user.preferred_time = None
    db.commit()

    return booking


def notify_owner(booking, user):
    send_whatsapp_message(
        BUSINESS_OWNER_PHONE,
        f"""
📅 New Booking

Client Phone: {user.platform_user_id}
Condition: {booking.condition}
Date: {booking.preferred_date}
Time: {booking.preferred_time}
"""
    )


def process_message(phone: str, text: str):

    user, db = get_or_create_user("whatsapp", phone)

    try:
        # Update last seen
        user.last_seen = datetime.utcnow()
        db.commit()

        # 1️⃣ Save user message to memory
        db.add(Message(user_id=user.id, role="user", content=text))
        db.commit()

        # 2️⃣ Extract structured booking entities
        extract_entities(user, text)
        db.commit()

        # 3️⃣ Detect if returning user
        previous_assistant_messages = (
            db.query(Message)
            .filter(
                Message.user_id == user.id,
                Message.role == "assistant"
            )
            .count()
        )

        is_returning = previous_assistant_messages > 0

        # 4️⃣ Build system prompt
        system_prompt = build_system_prompt(user, is_returning)

        # 5️⃣ Fetch recent conversation history (last 8 messages)
        recent_messages = (
            db.query(Message)
            .filter(Message.user_id == user.id)
            .order_by(Message.timestamp.desc())
            .limit(8)
            .all()
        )

        recent_messages.reverse()

        # 6️⃣ Construct messages list for Groq
        messages = [
            {"role": "system", "content": system_prompt}
        ]

        for msg in recent_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # 7️⃣ Call LLM
        reply = call_llm(messages)

        # 8️⃣ Save assistant reply to memory
        db.add(Message(user_id=user.id, role="assistant", content=reply))
        db.commit()

        # 9️⃣ Send reply to user
        send_whatsapp_message(phone, reply)

        # 🔟 Silent booking detection
        if booking_ready(user):
            booking = create_booking(db, user)
            notify_owner(booking, user)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

        db.close()
