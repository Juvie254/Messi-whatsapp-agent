import re
from datetime import datetime
from memory import get_or_create_user
from entity_extractor import extract_entities
from context_builder import build_system_prompt
from llm import call_llm
from messaging import send_whatsapp_message
from models import Booking, Message
from db import SessionLocal
 
BUSINESS_OWNER_PHONE = "254141625276"  # TODO: 
 
 
def booking_ready(user):
    return (
        user.viewing_date and
        user.viewing_time and
        user.client_name  # name captured = serious buyer
    )
 
 
def create_booking(db, user):
    booking = Booking(
        user_id=user.id,
        client_name=user.client_name,
        property_interest=user.preferred_location,
        viewing_date=user.viewing_date,
        viewing_time=user.viewing_time
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
 
    # Clear viewing fields after booking saved
    user.viewing_date = None
    user.viewing_time = None
    db.commit()
    return booking
 
 
def notify_owner(booking, user):
    send_whatsapp_message(
        BUSINESS_OWNER_PHONE,
        f"""
🏠 New Viewing Booked!
Client: {booking.client_name or 'Unknown'}
Phone: {user.platform_user_id}
Location Interest: {booking.property_interest or 'Not specified'}
Date: {booking.viewing_date}
Time: {booking.viewing_time}
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
 
        # 9️⃣ Handle SEND_PHOTOS trigger or send normal reply
        if reply.startswith("SEND_PHOTOS:"):
            from context_builder import PROPERTY_LISTINGS
            from messaging import send_whatsapp_image
 
            # Extract the first number found after the colon, instead of
            # assuming the whole remainder is a clean integer. Protects
            # against replies like "SEND_PHOTOS: 3 here are some options".
            match = re.search(r"\d+", reply.split(":", 1)[1])
            property = None
            if match:
                property_id = int(match.group())
                property = next(
                    (p for p in PROPERTY_LISTINGS if p["id"] == property_id),
                    None
                )
 
            if property:
                # .get() instead of direct indexing so a listing missing
                # price_rent/price_sale doesn't crash the whole request.
                price = property.get("price_rent") or property.get("price_sale")
                send_whatsapp_image(
                    phone,
                    property["image_url"],
                    f"{property['type']} – {property['location']}\n{price}"
                )
            else:
                send_whatsapp_message(phone, "I'll get the photos from our agent shortly! 📸")
        else:
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
