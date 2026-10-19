import logging
import time

from app.website_legal_extractor import extract_legal_signals_from_website


logger = logging.getLogger(__name__)


def get_effective_max_websites(max_websites_to_check: int) -> int | None:
    if max_websites_to_check <= 0:
        return None

    return max_websites_to_check


def build_legal_entity_candidates(
    businesses: list[dict],
    scraped_at: str,
    max_websites: int | None = None,
) -> list[dict]:
    candidates = []

    businesses_with_websites = [
        business
        for business in businesses
        if business.get("website")
    ]

    if max_websites is not None:
        businesses_with_websites = businesses_with_websites[:max_websites]

    logger.info(
        "Checking legal signals for %s business websites",
        len(businesses_with_websites),
    )

    for business in businesses_with_websites:
        website = business.get("website")
        business_name = business.get("business_name")

        logger.debug(
            "Extracting legal signals business=%s website=%s",
            business_name,
            website,
        )

        legal_signals = extract_legal_signals_from_website(
            website=website,
            max_pages=8,
        )

        if not legal_signals:
            continue

        candidate = {
            "google_place_id": business.get("google_place_id"),
            "business_name": business_name,
            "website": legal_signals.get("website"),
            "evidence_url": legal_signals.get("evidence_url"),
            "legal_name": legal_signals.get("legal_name"),
            "legal_form": legal_signals.get("legal_form"),
            "company_code": legal_signals.get("company_code"),
            "vat_code": legal_signals.get("vat_code"),
            "match_source": legal_signals.get("match_source"),
            "confidence_level": legal_signals.get("confidence_level"),
            "checked_pages": legal_signals.get("checked_pages"),
            "scraped_at": scraped_at,
        }

        candidates.append(candidate)

        logger.debug(
            (
                "Legal candidate business=%s | confidence=%s | "
                "legal_name=%s | company_code=%s | vat_code=%s"
            ),
            business_name,
            candidate.get("confidence_level"),
            candidate.get("legal_name"),
            candidate.get("company_code"),
            candidate.get("vat_code"),
        )

        time.sleep(1)

    return candidates