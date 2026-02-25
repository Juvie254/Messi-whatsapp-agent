from sqlalchemy.orm import Session
from datetime import datetime
from db import SessionLocal
from models import User

def get_or_create_user(platform: str, platform_user_id: str):
    db: Session = SessionLocal()

    user = (
        db.query(User)
        .filter(
            User.platform == platform,
            User.platform_user_id == platform_user_id
        )
        .first()
    )

    if not user:
        user = User(
            platform=platform,
            platform_user_id=platform_user_id,
            #state="NEW",
            last_seen=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.last_seen = datetime.utcnow()
        db.commit()

    return user, db
