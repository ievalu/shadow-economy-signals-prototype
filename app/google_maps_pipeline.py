import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.activity_scoring import calculate_google_activity_score
from app.database import (
    insert_google_activity_scores,
    insert_google_maps_business_snapshots,
    insert_google_maps_businesses,
)
from app.serpapi_client import (
    SerpApiClient,
    parse_google_maps_businesses,
)


logger = logging.getLogger(__name__)


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


def process_category_job(
    settings,
    client: Optional[SerpApiClient],
    connection,
    job: dict,
    run_id: str,
) -> tuple[int, int, list[dict]]:
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
        return 0, 0, []

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
        if client is None:
            raise ValueError("SerpApi client is required in live mode")

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

    insert_google_maps_business_snapshots(
        connection=connection,
        run_id=run_id,
        businesses=businesses,
    )

    calculated_at = datetime.now(timezone.utc).isoformat()

    score_records = build_activity_score_records(
        businesses=businesses,
        calculated_at=calculated_at,
    )

    insert_google_activity_scores(
        connection=connection,
        score_records=score_records,
    )

    logger.info(
        "Saved category=%s | businesses=%s | activity_scores=%s",
        category_key,
        len(businesses),
        len(score_records),
    )

    return len(businesses), len(score_records), businesses