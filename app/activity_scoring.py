import re
import unicodedata


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.lower().strip()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

    value = re.sub(r"\s+", " ", value)

    return value


def safe_int(value, default: int = 0) -> int:
    if value is None:
        return default

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    value = str(value)
    value = re.sub(r"[^\d]", "", value)

    if not value:
        return default

    return int(value)


def safe_float(value, default: float = 0.0) -> float:
    if value is None:
        return default

    if isinstance(value, int | float):
        return float(value)

    value = str(value).replace(",", ".")
    value = re.sub(r"[^0-9.]", "", value)

    if not value:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def classify_open_state(open_state: str | None) -> str:
    value = normalize_text(open_state)

    if not value:
        return "unknown"

    if (
        "permanently closed" in value
        or "closed permanently" in value
        or "visam laikui uzdaryta" in value
        or "uzdaryta visam laikui" in value
    ):
        return "permanently_closed"

    if (
        "temporarily closed" in value
        or "laikinai uzdaryta" in value
    ):
        return "temporarily_closed"

    # Check normal closed state before open,
    # because values like "Closed ⋅ Opens 9 AM" contain "open".
    if (
        value.startswith("closed")
        or value.startswith("uzdaryta")
        or "closed ⋅ opens" in value
        or "closed · opens" in value
        or "uzdaryta ⋅" in value
        or "uzdaryta ·" in value
    ):
        return "closed_now"

    if (
        value.startswith("open")
        or value.startswith("atidaryta")
        or "open 24 hours" in value
        or "dirba visa para" in value
    ):
        return "open_now"

    return "unknown"


def get_review_count_score(google_review_count: int) -> tuple[int, list[str]]:
    if google_review_count >= 1000:
        return 15, ["google_reviews_1000_plus"]

    if google_review_count >= 200:
        return 9, ["google_reviews_200_plus"]

    if google_review_count >= 50:
        return 5, ["google_reviews_50_plus"]

    if google_review_count >= 10:
        return 2, ["google_reviews_10_plus"]

    return 0, []


def calculate_google_activity_score(business: dict) -> dict:
    score = 0
    reasons = []

    google_review_count = safe_int(business.get("google_review_count"))
    google_rating = safe_float(business.get("google_rating"))

    open_state = business.get("open_state") or ""
    hours = business.get("hours")
    operating_hours = business.get("operating_hours")

    review_score, review_reasons = get_review_count_score(google_review_count)

    score += review_score
    reasons.extend(review_reasons)

    if google_rating >= 4.0 and google_review_count >= 20:
        score += 2
        reasons.append("high_rating_with_meaningful_review_count")

    if business.get("phone"):
        score += 1
        reasons.append("phone_exists")

    if business.get("website"):
        score += 1
        reasons.append("website_exists")

    if business.get("address"):
        score += 1
        reasons.append("address_exists")

    if open_state:
        score += 1
        reasons.append("open_state_exists")

        open_state_class = classify_open_state(open_state)

        if open_state_class == "open_now":
            score += 2
            reasons.append("open_now")

        elif open_state_class == "closed_now":
            reasons.append("closed_now_normal_schedule")

        elif open_state_class == "temporarily_closed":
            score -= 3
            reasons.append("temporarily_closed")

        elif open_state_class == "permanently_closed":
            score -= 8
            reasons.append("permanently_closed")

        else:
            reasons.append("open_state_unknown")

    if hours:
        score += 1
        reasons.append("hours_exists")

    if operating_hours:
        score += 1
        reasons.append("operating_hours_exists")

    if score >= 15:
        activity_level = "high"
    elif score >= 8:
        activity_level = "medium"
    else:
        activity_level = "low"

    return {
        "google_activity_score": score,
        "google_activity_level": activity_level,
        "google_activity_reasons": reasons,
    }