# entity_extractor.py - Real Estate Version
import re

NAIROBI_AREAS = [
    "kilimani", "westlands", "lavington", "karen", "runda",
    "syokimau", "ruiru", "kasarani", "eastleigh", "south b",
    "south c", "langata", "ngong", "kitengela", "rongai",
    "embakasi", "donholm", "umoja", "buruburu", "thika road",
    "kiambu road", "waiyaki way", "mombasa road", "cbd"
]

def extract_entities(user, text: str):
    t = text.lower()

    # --- Buy or Rent Intent ---
    if any(w in t for w in ["buy", "purchase", "own", "sale", "for sale"]):
        user.intent = "buy"
    elif any(w in t for w in ["rent", "rental", "tenant", "lease", "to let"]):
        user.intent = "rent"

    # --- Bedrooms ---
    bedroom_match = re.search(
        r"(\d+)\s*(bed|bedroom|bedrooms|br)\b", t
    )
    if bedroom_match:
        user.bedrooms = bedroom_match.group(1)
    elif "bedsitter" in t or "bedsit" in t:
        user.bedrooms = "bedsitter"
    elif "studio" in t:
        user.bedrooms = "studio"

    # --- Budget (handles 50k, 50,000, 2M, 2 million) ---
    budget_match = re.search(
        r"(ksh\.?|kes|k)?\s*(\d+[\d,]*)\s*(k|m|million|thousand)?",
        t
    )
    if budget_match:
        raw = budget_match.group(2).replace(",", "")
        multiplier = budget_match.group(3) or ""
        amount = int(raw)
        if multiplier in ["m", "million"]:
            amount *= 1_000_000
        elif multiplier in ["k", "thousand"] or amount < 1000:
            amount *= 1000
        if amount >= 10_000:  # filter noise
            user.budget = str(amount)

    # --- Location ---
    for area in NAIROBI_AREAS:
        if area in t:
            user.preferred_location = area.title()
            break

    # --- Viewing Date ---
    date_keywords = [
        "today", "tomorrow", "monday", "tuesday",
        "wednesday", "thursday", "friday", "saturday",
        "sunday", "leo", "kesho", "weekend"
    ]
    for keyword in date_keywords:
        if keyword in t:
            user.viewing_date = keyword
            break

    # --- Viewing Time ---
    time_match = re.search(
        r"\b(\d{1,2}(:\d{2})?\s?(am|pm)?)\b", t
    )
    if time_match:
        user.viewing_time = time_match.group(0)

    # --- Client Name (simple capture) ---
    name_match = re.search(
        r"(my name is|i[''`]?m|call me|ni mimi)\s+([A-Z][a-z]+)",
        text,
        re.IGNORECASE
    )
    if name_match:
        user.client_name = name_match.group(2)