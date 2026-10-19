import re
import unicodedata


def normalize_whitespace(value: str | None) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return re.sub(r"\s+", " ", value)


def remove_diacritics(value: str) -> str:
    normalized_value = unicodedata.normalize("NFKD", value)

    return "".join(
        character
        for character in normalized_value
        if not unicodedata.combining(character)
    )


def normalize_text(value: str | None) -> str | None:
    value = normalize_whitespace(value)

    if not value:
        return None

    value = value.lower()
    value = remove_diacritics(value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = normalize_whitespace(value)

    return value


def normalize_name(value: str | None) -> str | None:
    value = normalize_text(value)

    if not value:
        return None

    legal_form_replacements = {
        "uzdaroji akcine bendrove": "",
        "mazoji bendrija": "",
        "akcine bendrove": "",
        "viesoji istaiga": "",
        "individuali imone": "",
        "uab": "",
        "mb": "",
        "ab": "",
        "vsi": "",
        "ii": "",
    }

    for old_value, new_value in legal_form_replacements.items():
        value = value.replace(old_value, new_value)

    value = value.replace('"', " ")
    value = value.replace("„", " ")
    value = value.replace("“", " ")

    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = normalize_whitespace(value)

    return value


def fix_mojibake(value: str | None) -> str | None:
    """
    Fix common UTF-8 text accidentally decoded as Latin-1/Windows-1252.

    Example:
        UÅ¾daroji akcinÄ— bendrovÄ—
    becomes:
        Uždaroji akcinė bendrovė
    """
    if not value:
        return value

    mojibake_markers = ["Å", "Ä", "Æ", "Ð", "Ø", "Ã"]

    if not any(marker in value for marker in mojibake_markers):
        return value

    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value