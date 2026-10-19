import logging
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


LEGAL_NAME_PREFIX_QUOTED_PATTERN = re.compile(
    r'\b(UAB|MB|AB|VšĮ|VSI|IĮ|II)\s+[„"]([^"„“<>]{2,120})[“"]',
    re.IGNORECASE,
)

LEGAL_NAME_PREFIX_UNQUOTED_PATTERN = re.compile(
    r'\b(UAB|MB|AB|VšĮ|VSI|IĮ|II)\s+([A-ZĄČĘĖĮŠŲŪŽ][^,\n<>]{2,80})',
    re.IGNORECASE,
)

LEGAL_NAME_SUFFIX_PATTERN = re.compile(
    r'([A-ZĄČĘĖĮŠŲŪŽ][A-Za-zĄČĘĖĮŠŲŪŽąčęėįšųūž0-9\s&\.\-]{2,100})'
    r'\s*,?\s+\b(UAB|MB|AB|VšĮ|VSI|IĮ|II)\b',
    re.IGNORECASE,
)

COMPANY_CODE_PATTERN = re.compile(
    r"(?:įmonės\s+kodas|imones\s+kodas|juridinio\s+asmens\s+kodas|company\s+code)"
    r"[\s:–-]*([0-9]{7,9})",
    re.IGNORECASE,
)

VAT_CODE_PATTERN = re.compile(
    r"(?:pvm\s+kodas|pvm\s+mokėtojo\s+kodas|vat\s+code)"
    r"[\s:–-]*(LT[0-9]{9,12})",
    re.IGNORECASE,
)


BAD_LEGAL_NAME_KEYWORDS = [
    "įmonės kodas",
    "imones kodas",
    "juridinio asmens kodas",
    "pvm kodas",
    "vat code",
    "adresas",
    "address",
    "telefonas",
    "phone",
    "el. paštas",
    "email",
    "privatumo politika",
    "privacy policy",
    "duomenų valdytojas",
    "data controller",
    "slapukai",
    "cookies",
    "kontaktai",
    "contacts",
]


LEGAL_PAGE_PATHS = [
    "",
    "rekvizitai",
    "kontaktai",
    "privatumo-politika",
    "contacts",
    "contact",
    "privacy-policy",
    "privacy",
    "apie-mus",
    "apie",
    "about",
    "taisykles",
    "terms",
    "terms-and-conditions",
]


def normalize_website_url(website: str | None) -> str | None:
    if not website:
        return None

    website = website.strip()

    if not website:
        return None

    if not website.startswith(("http://", "https://")):
        website = f"https://{website}"

    return website


def get_base_url(website: str) -> str:
    parsed_url = urlparse(website)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


def build_candidate_urls(website: str) -> list[str]:
    normalized_website = normalize_website_url(website)

    if not normalized_website:
        return []

    base_url = get_base_url(normalized_website)

    candidate_urls = []

    for path in LEGAL_PAGE_PATHS:
        if path:
            candidate_urls.append(urljoin(base_url, path))
        else:
            candidate_urls.append(base_url)

    return list(dict.fromkeys(candidate_urls))


def fetch_url(url: str, timeout_seconds: int = 15) -> str | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 compatible; ShadowEconomyResearchBot/1.0"
        )
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout_seconds,
            allow_redirects=True,
        )

        if response.status_code >= 400:
            logger.debug(
                "Skipping URL due to status_code=%s url=%s",
                response.status_code,
                url,
            )
            return None

        content_type = response.headers.get("content-type", "").lower()

        if "text/html" not in content_type and "text/plain" not in content_type:
            logger.debug(
                "Skipping non-html URL content_type=%s url=%s",
                content_type,
                url,
            )
            return None

        return response.text

    except requests.RequestException as error:
        logger.debug("Failed to fetch url=%s error=%s", url, error)
        return None


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    return "\n".join(lines)


def clean_legal_name(raw_value: str | None) -> str | None:
    if not raw_value:
        return None

    value = raw_value.strip()
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" ,.;:-–—")

    return value or None


def is_bad_legal_name_candidate(value: str | None) -> bool:
    if not value:
        return True

    normalized_value = value.lower().strip()

    if len(normalized_value) < 3:
        return True

    if len(normalized_value) > 120:
        return True

    for keyword in BAD_LEGAL_NAME_KEYWORDS:
        if keyword in normalized_value:
            return True

    if normalized_value.count(" ") > 8:
        return True

    return False


def normalize_legal_name(legal_form: str, name_body: str) -> str | None:
    legal_form = legal_form.strip()
    name_body = clean_legal_name(name_body)

    if not name_body:
        return None

    if is_bad_legal_name_candidate(name_body):
        return None

    return f"{legal_form} {name_body}"


def calculate_confidence_level(
    legal_name: str | None,
    company_code: str | None,
    vat_code: str | None,
) -> str:
    if company_code and legal_name:
        return "high"

    if company_code or vat_code:
        return "medium"

    if legal_name:
        return "low"

    return "none"


def extract_legal_name_from_text(text: str) -> tuple[str | None, str | None]:
    prefix_quoted_match = LEGAL_NAME_PREFIX_QUOTED_PATTERN.search(text)

    if prefix_quoted_match:
        legal_form = prefix_quoted_match.group(1)
        name_body = prefix_quoted_match.group(2)

        legal_name = normalize_legal_name(
            legal_form=legal_form,
            name_body=name_body,
        )

        if legal_name:
            return legal_name, legal_form

    suffix_match = LEGAL_NAME_SUFFIX_PATTERN.search(text)

    if suffix_match:
        name_body = suffix_match.group(1)
        legal_form = suffix_match.group(2)

        legal_name = normalize_legal_name(
            legal_form=legal_form,
            name_body=name_body,
        )

        if legal_name:
            return legal_name, legal_form

    prefix_unquoted_match = LEGAL_NAME_PREFIX_UNQUOTED_PATTERN.search(text)

    if prefix_unquoted_match:
        legal_form = prefix_unquoted_match.group(1)
        name_body = prefix_unquoted_match.group(2)

        legal_name = normalize_legal_name(
            legal_form=legal_form,
            name_body=name_body,
        )

        if legal_name:
            return legal_name, legal_form

    return None, None


def extract_legal_signals_from_text(text: str, evidence_url: str) -> dict:
    company_code_match = COMPANY_CODE_PATTERN.search(text)
    vat_code_match = VAT_CODE_PATTERN.search(text)

    legal_name, legal_form = extract_legal_name_from_text(text)

    company_code = None

    if company_code_match:
        company_code = company_code_match.group(1)

    vat_code = None

    if vat_code_match:
        vat_code = vat_code_match.group(1)

    found_anything = any([
        legal_name,
        company_code,
        vat_code,
    ])

    if not found_anything:
        return {}

    return {
        "evidence_url": evidence_url,
        "legal_name": legal_name,
        "legal_form": legal_form,
        "company_code": company_code,
        "vat_code": vat_code,
        "match_source": "business_website",
        "confidence_level": calculate_confidence_level(
            legal_name=legal_name,
            company_code=company_code,
            vat_code=vat_code,
        ),
    }


def merge_legal_signals(
    website: str,
    collected_signals: list[dict],
    checked_pages: list[str],
) -> dict:
    merged = {
        "website": website,
        "evidence_url": None,
        "legal_name": None,
        "legal_form": None,
        "company_code": None,
        "vat_code": None,
        "match_source": "business_website",
        "confidence_level": "none",
        "checked_pages": checked_pages,
    }

    evidence_urls = []

    for signal in collected_signals:
        if not merged["legal_name"] and signal.get("legal_name"):
            merged["legal_name"] = signal.get("legal_name")

        if not merged["legal_form"] and signal.get("legal_form"):
            merged["legal_form"] = signal.get("legal_form")

        if not merged["company_code"] and signal.get("company_code"):
            merged["company_code"] = signal.get("company_code")

        if not merged["vat_code"] and signal.get("vat_code"):
            merged["vat_code"] = signal.get("vat_code")

        if signal.get("evidence_url"):
            evidence_urls.append(signal["evidence_url"])

    merged["evidence_url"] = " | ".join(list(dict.fromkeys(evidence_urls))) or None

    merged["confidence_level"] = calculate_confidence_level(
        legal_name=merged["legal_name"],
        company_code=merged["company_code"],
        vat_code=merged["vat_code"],
    )

    return merged


def extract_legal_signals_from_website(
    website: str | None,
    max_pages: int = 8,
) -> dict | None:
    normalized_website = normalize_website_url(website)

    if not normalized_website:
        return None

    candidate_urls = build_candidate_urls(normalized_website)
    checked_pages = candidate_urls[:max_pages]

    logger.info(
        "Checking website legal signals website=%s candidate_pages=%s",
        normalized_website,
        len(checked_pages),
    )

    collected_signals = []

    for url in checked_pages:
        html = fetch_url(url)

        if not html:
            continue

        text = html_to_text(html)

        legal_signals = extract_legal_signals_from_text(
            text=text,
            evidence_url=url,
        )

        if legal_signals:
            collected_signals.append(legal_signals)

    if not collected_signals:
        return {
            "website": normalized_website,
            "evidence_url": None,
            "legal_name": None,
            "legal_form": None,
            "company_code": None,
            "vat_code": None,
            "match_source": "business_website",
            "confidence_level": "none",
            "checked_pages": checked_pages,
        }

    return merge_legal_signals(
        website=normalized_website,
        collected_signals=collected_signals,
        checked_pages=checked_pages,
    )