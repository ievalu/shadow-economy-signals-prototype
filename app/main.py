import json
import logging
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from app.activity_scoring import calculate_google_activity_score
from app.config import get_settings
from app.database import (
    create_tables,
    get_connection,
    insert_google_activity_scores,
    insert_google_maps_businesses,
    insert_legal_entity_candidates,
    insert_rc_verifications,
)
from app.serpapi_client import (
    SerpApiClient,
    parse_google_maps_businesses,
)
from app.website_legal_extractor import extract_legal_signals_from_website


logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO") -> None:
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def save_json(data: dict, file_path: str) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_sample_google_maps_response(sample_path: str) -> dict:
    path = Path(sample_path)

    if not path.exists():
        raise FileNotFoundError(f"Sample Google Maps file not found: {sample_path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_category_query_map(city: str) -> dict[str, dict]:
    return {
        "food": {
            "category_key": "food",
            "query": "restaurants",
            "display_name": f"restaurants in {city}",
        },
        "beauty": {
            "category_key": "beauty",
            "query": "beauty salons",
            "display_name": f"beauty salons in {city}",
        },
        "cars": {
            "category_key": "cars",
            "query": "car repair",
            "display_name": f"car repair in {city}",
        },
    }


def get_selected_category_jobs(
    city: str,
    selected_categories: list[str],
    max_categories: int,
) -> list[dict]:
    category_query_map = get_category_query_map(city)
    limited_categories = selected_categories[:max_categories]

    jobs = []

    for category_key in limited_categories:
        if category_key not in category_query_map:
            raise ValueError(
                f"Unsupported category: {category_key}. "
                f"Supported categories: {list(category_query_map.keys())}"
            )

        jobs.append(category_query_map[category_key])

    return jobs


def scrape_google_maps_paginated(
    client: SerpApiClient,
    query: str,
    category_key: str,
    latitude: float,
    longitude: float,
    zoom: int,
    language: str,
    country: str,
    max_pages: int,
) -> tuple[list[dict], list[dict]]:
    all_businesses = []
    raw_pages = []

    data = client.search_google_maps(
        query=query,
        latitude=latitude,
        longitude=longitude,
        zoom=zoom,
        language=language,
        country=country,
    )

    page_number = 1

    while True:
        raw_pages.append({
            "page_number": page_number,
            "data": data,
        })

        businesses = parse_google_maps_businesses(
            data=data,
            category_key=category_key,
            search_query=query,
        )

        all_businesses.extend(businesses)

        next_url = data.get("serpapi_pagination", {}).get("next")

        if not next_url:
            break

        if page_number >= max_pages:
            break

        logger.info(
            "Fetching next SerpApi page category=%s query=%s page=%s",
            category_key,
            query,
            page_number + 1,
        )

        data = client.get_next_page(next_url)
        page_number += 1

        time.sleep(1)

    return all_businesses, raw_pages


def deduplicate_businesses_by_place_id(businesses: list[dict]) -> list[dict]:
    seen_place_ids = set()
    deduplicated = []

    for business in businesses:
        place_id = business.get("google_place_id")

        if not place_id:
            deduplicated.append(business)
            continue

        if place_id in seen_place_ids:
            continue

        seen_place_ids.add(place_id)
        deduplicated.append(business)

    return deduplicated


def build_activity_score_records(
    businesses: list[dict],
    calculated_at: str,
) -> list[dict]:
    score_records = []

    for business in businesses:
        activity_score = calculate_google_activity_score(business)

        score_records.append({
            "google_place_id": business.get("google_place_id"),
            "business_name": business.get("business_name"),
            "category_key": business.get("category_key"),
            "google_activity_score": activity_score["google_activity_score"],
            "google_activity_level": activity_score["google_activity_level"],
            "google_activity_reasons": activity_score["google_activity_reasons"],
            "calculated_at": calculated_at,
        })

    return score_records


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

        logger.info(
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

        logger.info(
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


def normalize_name(value: str | None) -> str | None:
    if not value:
        return None

    value = value.lower().strip()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )

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
        "všį": "",
        "ii": "",
        "iį": "",
    }

    for old_value, new_value in legal_form_replacements.items():
        value = value.replace(old_value, new_value)

    value = value.replace('"', " ")
    value = value.replace("„", " ")
    value = value.replace("“", " ")

    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip() or None


def find_rc_match(connection, candidate: dict):
    company_code = candidate.get("company_code")
    legal_name = candidate.get("legal_name")

    if company_code:
        row = connection.execute("""
            SELECT
                ja_kodas,
                ja_pavadinimas,
                form_pavadinimas,
                stat_pavadinimas
            FROM rc_entities
            WHERE ja_kodas = ?
            LIMIT 1
        """, (company_code,)).fetchone()

        if row:
            return "matched", "company_code", row

    if legal_name:
        normalized_candidate_name = normalize_name(legal_name)

        if normalized_candidate_name:
            rows = connection.execute("""
                SELECT
                    ja_kodas,
                    ja_pavadinimas,
                    form_pavadinimas,
                    stat_pavadinimas
                FROM rc_entities
                WHERE ja_pavadinimas IS NOT NULL
            """).fetchall()

            for row in rows:
                normalized_rc_name = normalize_name(row["ja_pavadinimas"])

                if normalized_rc_name == normalized_candidate_name:
                    return "matched", "legal_name_normalized_exact", row

            for row in rows:
                normalized_rc_name = normalize_name(row["ja_pavadinimas"])

                if not normalized_rc_name:
                    continue

                if (
                    normalized_candidate_name in normalized_rc_name
                    or normalized_rc_name in normalized_candidate_name
                ):
                    return "matched", "legal_name_normalized_partial", row

    return "not_found", None, None


def get_latest_rc_financial_value(
    connection,
    ja_kodas: str,
    line_name_keywords: list[str],
) -> float | None:
    rows = connection.execute("""
        SELECT
            line_name,
            reiksme,
            turning_date,
            reg_date
        FROM rc_financial_records
        WHERE ja_kodas = ?
          AND reiksme IS NOT NULL
        ORDER BY
            turning_date DESC,
            reg_date DESC
    """, (ja_kodas,)).fetchall()

    for row in rows:
        normalized_line_name = normalize_name(row["line_name"])

        if not normalized_line_name:
            continue

        for keyword in line_name_keywords:
            normalized_keyword = normalize_name(keyword)

            if normalized_keyword and normalized_keyword in normalized_line_name:
                return row["reiksme"]

    return None


def build_rc_verification_records(
    connection,
    checked_at: str,
) -> list[dict]:
    candidates = connection.execute("""
        SELECT
            google_place_id,
            business_name,
            legal_name,
            company_code,
            vat_code
        FROM legal_entity_candidates
    """).fetchall()

    records = []

    for candidate_row in candidates:
        candidate = {
            "google_place_id": candidate_row["google_place_id"],
            "business_name": candidate_row["business_name"],
            "legal_name": candidate_row["legal_name"],
            "company_code": candidate_row["company_code"],
            "vat_code": candidate_row["vat_code"],
        }

        match_status, match_method, rc_row = find_rc_match(
            connection=connection,
            candidate=candidate,
        )

        rc_latest_revenue = None
        rc_latest_profit = None

        if rc_row:
            rc_latest_revenue = get_latest_rc_financial_value(
                connection=connection,
                ja_kodas=rc_row["ja_kodas"],
                line_name_keywords=[
                    "PARDAVIMO PAJAMOS",
                ],
            )

            rc_latest_profit = get_latest_rc_financial_value(
                connection=connection,
                ja_kodas=rc_row["ja_kodas"],
                line_name_keywords=[
                    "GRYNASIS PELNAS",
                    "ATASKAITINIŲ METŲ PELNAS",
                    "PELNAS",
                ],
            )

        records.append({
            "google_place_id": candidate.get("google_place_id"),
            "business_name": candidate.get("business_name"),
            "website_legal_name": candidate.get("legal_name"),
            "website_company_code": candidate.get("company_code"),
            "website_vat_code": candidate.get("vat_code"),
            "match_status": match_status,
            "match_method": match_method,
            "rc_ja_kodas": rc_row["ja_kodas"] if rc_row else None,
            "rc_ja_pavadinimas": rc_row["ja_pavadinimas"] if rc_row else None,
            "rc_form_pavadinimas": rc_row["form_pavadinimas"] if rc_row else None,
            "rc_stat_pavadinimas": rc_row["stat_pavadinimas"] if rc_row else None,
            "rc_latest_revenue": rc_latest_revenue,
            "rc_latest_profit": rc_latest_profit,
            "checked_at": checked_at,
        })

        logger.info(
            (
                "RC check business=%s | legal_name=%s | company_code=%s | "
                "status=%s | method=%s | rc_name=%s"
            ),
            candidate.get("business_name"),
            candidate.get("legal_name"),
            candidate.get("company_code"),
            match_status,
            match_method,
            rc_row["ja_pavadinimas"] if rc_row else None,
        )

    return records


def print_final_results(connection) -> None:
    rows = connection.execute("""
        SELECT
            b.business_name,
            b.category_key,
            b.google_rating,
            b.google_review_count,
            b.open_state,
            b.website,
            s.google_activity_score,
            s.google_activity_level,
            l.legal_name,
            l.company_code,
            l.vat_code,
            l.confidence_level,
            r.match_status,
            r.match_method,
            r.rc_ja_kodas,
            r.rc_ja_pavadinimas,
            r.rc_latest_revenue,
            r.rc_latest_profit
        FROM google_maps_businesses AS b
        LEFT JOIN google_activity_scores AS s
            ON b.google_place_id = s.google_place_id
        LEFT JOIN legal_entity_candidates AS l
            ON b.google_place_id = l.google_place_id
        LEFT JOIN rc_verifications AS r
            ON b.google_place_id = r.google_place_id
        ORDER BY
            s.google_activity_score DESC,
            b.google_review_count DESC
        LIMIT 30
    """).fetchall()

    logger.info("Final results:")

    for row in rows:
        logger.info(
            (
                "Name=%s | Category=%s | Reviews=%s | Activity=%s/%s | "
                "Website legal=%s | Code=%s | VAT=%s | "
                "RC=%s via %s | RC name=%s | Revenue=%s | Profit=%s"
            ),
            row["business_name"],
            row["category_key"],
            row["google_review_count"],
            row["google_activity_score"],
            row["google_activity_level"],
            row["legal_name"],
            row["company_code"],
            row["vat_code"],
            row["match_status"],
            row["match_method"],
            row["rc_ja_pavadinimas"],
            row["rc_latest_revenue"],
            row["rc_latest_profit"],
        )


def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info("Starting shadow economy activity scraper")
    logger.info("App mode: %s", settings.app_mode)
    logger.info("Provider: %s", settings.provider)
    logger.info("City: %s", settings.scrape_city)
    logger.info("Categories: %s", settings.scrape_categories)
    logger.info("Max categories: %s", settings.max_categories)
    logger.info("Database path: %s", settings.database_path)
    logger.info("SerpApi max pages: %s", settings.serpapi_max_pages)

    if settings.app_mode != "demo" and settings.provider != "serpapi":
        raise NotImplementedError(
            f"Provider '{settings.provider}' is not implemented in main.py yet"
        )

    if settings.app_mode != "demo" and not settings.serpapi_api_key:
        raise ValueError("SERPAPI_API_KEY is missing")

    client = None

    if settings.app_mode != "demo":
        client = SerpApiClient(
            api_key=settings.serpapi_api_key,
        )

    connection = get_connection(settings.database_path)
    create_tables(connection)

    jobs = get_selected_category_jobs(
        city=settings.scrape_city,
        selected_categories=settings.scrape_categories,
        max_categories=settings.max_categories,
    )

    logger.info("Total category jobs: %s", len(jobs))

    total_businesses_saved = 0
    total_scores_saved = 0
    total_legal_candidates_saved = 0

    for job in jobs:
        category_key = job["category_key"]
        query = job["query"]
        display_name = job["display_name"]

        logger.info(
            "Processing category=%s display_name=%s query=%s",
            category_key,
            display_name,
            query,
        )

        if settings.dry_run:
            logger.info("DRY_RUN enabled. Skipping API request for query=%s", query)
            continue

        if settings.app_mode == "demo":
            logger.info(
                "APP_MODE=demo. Loading sample Google Maps response from %s",
                settings.sample_google_maps_path,
            )

            data = load_sample_google_maps_response(
                sample_path=settings.sample_google_maps_path,
            )

            businesses = parse_google_maps_businesses(
                data=data,
                category_key=category_key,
                search_query=query,
            )

            raw_pages = [
                {
                    "page_number": 1,
                    "data": data,
                }
            ]

        else:
            businesses, raw_pages = scrape_google_maps_paginated(
                client=client,
                query=query,
                category_key=category_key,
                latitude=settings.map_latitude,
                longitude=settings.map_longitude,
                zoom=settings.map_zoom,
                language=settings.map_language,
                country=settings.map_country,
                max_pages=settings.serpapi_max_pages,
            )

        for raw_page in raw_pages:
            page_number = raw_page["page_number"]
            data = raw_page["data"]

            raw_file_name = (
                f"{category_key}_{query.replace(' ', '_')}_"
                f"{settings.scrape_city.lower()}_page_{page_number}.json"
            )
            raw_file_path = f"data/raw_serpapi/{raw_file_name}"

            save_json(
                data=data,
                file_path=raw_file_path,
            )

        businesses = deduplicate_businesses_by_place_id(businesses)

        scraped_at = datetime.now(timezone.utc).isoformat()

        for business in businesses:
            business["scraped_at"] = scraped_at

        insert_google_maps_businesses(
            connection=connection,
            businesses=businesses,
        )

        total_businesses_saved += len(businesses)

        calculated_at = datetime.now(timezone.utc).isoformat()

        score_records = build_activity_score_records(
            businesses=businesses,
            calculated_at=calculated_at,
        )

        insert_google_activity_scores(
            connection=connection,
            score_records=score_records,
        )

        total_scores_saved += len(score_records)

        if settings.app_mode == "demo":
            logger.info("APP_MODE=demo. Skipping website legal extraction.")
            legal_candidates = []
        else:
            legal_candidates = build_legal_entity_candidates(
                businesses=businesses,
                scraped_at=scraped_at,
                max_websites=None,
            )

        insert_legal_entity_candidates(
            connection=connection,
            candidates=legal_candidates,
        )

        total_legal_candidates_saved += len(legal_candidates)

        logger.info(
            (
                "Saved category=%s | businesses=%s | activity_scores=%s | "
                "legal_candidates=%s"
            ),
            category_key,
            len(businesses),
            len(score_records),
            len(legal_candidates),
        )

        time.sleep(settings.request_delay_seconds)

    checked_at = datetime.now(timezone.utc).isoformat()

    rc_verification_records = build_rc_verification_records(
        connection=connection,
        checked_at=checked_at,
    )

    insert_rc_verifications(
        connection=connection,
        records=rc_verification_records,
    )

    logger.info("Saved %s RC verification records", len(rc_verification_records))

    print_final_results(connection)

    connection.close()

    logger.info("Finished scraper")
    logger.info("Total businesses saved: %s", total_businesses_saved)
    logger.info("Total activity scores saved: %s", total_scores_saved)
    logger.info("Total legal candidates saved: %s", total_legal_candidates_saved)


if __name__ == "__main__":
    main()