def extract_entities(user, text: str):
    import re
    t = text.lower()

    # ----------------
    # Detect date (English + Kiswahili)
    # ----------------
    date_keywords = [
        "today", "tomorrow",
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "leo", "kesho"
    ]

    for keyword in date_keywords:
        if keyword in t:
            user.preferred_date = keyword
            break

    # ----------------
    # Detect time
    # ----------------
    time_match = re.search(r"\b\d{1,2}(:\d{2})?\s?(am|pm)?\b", t)
    if time_match:
        user.preferred_time = time_match.group(0)

    # ----------------
    # Detect possible health concern
    # ----------------
    health_indicators = [
        "pain", "shida", "problem", "suffer", "condition",
        "uchungu", "naumwa", "naskia", "sick"
    ]

    if any(word in t for word in health_indicators):
        user.condition = text.strip()
