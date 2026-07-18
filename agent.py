from datetime import datetime
from memory import get_or_create_user
from entity_extractor import extract_entities
from context_builder import build_system_prompt
from llm import call_llm
from messaging import send_whatsapp_message
from models import Booking, Message
from db import SessionLocal

BUSINESS_OWNER_PHONE = "254141625276"


def detect_language(text: str) -> str:
    swahili_words = [
        "habari", "nataka", "nyumba", "sawa", "nzuri", "karibu",
        "kupanga", "kuona", "hiyo", "nina", "naeza", "lakini",
        "unapatikana", "ungependa", "nione", "niambie", "natafuta",
        "bei", "lini", "wapi", "vipi", "ndiyo", "hapana", "asante",
        "tafadhali", "samahani", "nimepata", "ninataka", "sijui",
        "hebu", "safi", "poa", "mambo", "leo", "kesho", "wiki"
    ]
    text_lower = text.lower()
    swahili_count = sum(1 for word in swahili_words if word in text_lower)
    return "swahili" if swahili_count >= 1 else "english"


def booking_ready(user):
    return (
        user.viewing_date and
        user.viewing_time and
        user.client_name
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

        # 1️⃣ Save user message
        db.add(Message(user_id=user.id, role="user", content=text))
        db.commit()

        # 2️⃣ Extract entities
        extract_entities(user, text)
        db.commit()

        # 3️⃣ Detect returning user
        previous_assistant_messages = (
            db.query(Message)
            .filter(
                Message.user_id == user.id,
                Message.role == "assistant"
            )
            .count()
        )
        is_returning = previous_assistant_messages > 0

        # 4️⃣ Detect name state
        name_already_given = bool(user.client_name)

        # 5️⃣ Detect if name was refused by checking recent messages
        name_refused = False
        recent_all = (
            db.query(Message)
            .filter(Message.user_id == user.id)
            .order_by(Message.timestamp.desc())
            .limit(10)
            .all()
        )
        refusal_phrases = [
            "name is not important", "don't need my name", 
            "why do you need", "is name important",
            "jina si muhimu", "usiniulize jina", 
            "jina haihusiki", "si lazima jina"
        ]
        for msg in recent_all:
            if msg.role == "user":
                if any(phrase in msg.content.lower() for phrase in refusal_phrases):
                    name_refused = True
                    break

        # 6️⃣ Detect language from current message
        detected_lang = detect_language(text)

        # 7️⃣ Build system prompt with all context
        system_prompt = build_system_prompt(
            user,
            is_returning,
            name_already_given=name_already_given,
            name_refused=name_refused,
            detected_lang=detected_lang
        )

        # 8️⃣ Fetch recent conversation history (last 10 messages)
        recent_messages = (
            db.query(Message)
            .filter(Message.user_id == user.id)
            .order_by(Message.timestamp.desc())
            .limit(10)
            .all()
        )
        recent_messages.reverse()

        # 9️⃣ Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]
        for msg in recent_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # 🔟 Call LLM
        reply = call_llm(messages)

        # 1️⃣1️⃣ Save assistant reply
        db.add(Message(user_id=user.id, role="assistant", content=reply))
        db.commit()

        # 1️⃣2️⃣ Handle SEND_PHOTOS or normal reply
        if reply.strip().startswith("SEND_PHOTOS:"):
            try:
                property_id = int(reply.strip().split(":")[1].strip())
                from context_builder import PROPERTY_LISTINGS
                from messaging import send_whatsapp_image
                matched = next(
                    (p for p in PROPERTY_LISTINGS if p["id"] == property_id), 
                    None
                )
                if matched:
                    send_whatsapp_image(
                        phone,
                        matched["image_url"],
                        f"{matched['type']} – {matched['location']}\n"
                        f"{matched['price_rent'] or matched['price_sale']}"
                    )
                else:
                    send_whatsapp_message(
                        phone, 
                        "I'll get those photos from our agent shortly! 📸"
                    )
            except Exception as photo_error:
                print(f"Photo send error: {photo_error}")
                send_whatsapp_message(
                    phone, 
                    "I'll get those photos from our agent shortly! 📸"
                )
        else:
            send_whatsapp_message(phone, reply)

        # 1️⃣3️⃣ Silent booking detection
        if booking_ready(user):
            booking = create_booking(db, user)
            notify_owner(booking, user)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
