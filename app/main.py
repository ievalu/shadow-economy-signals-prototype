import logging
import time
from datetime import datetime, timezone
from typing import Optional

from app.category_config import get_selected_category_jobs
from app.config import get_settings
from app.database import (
    create_tables,
    get_connection,
    insert_legal_entity_candidates,
    insert_pipeline_run,
    insert_rc_verifications,
)
from app.google_maps_pipeline import process_category_job
from app.legal_pipeline import (
    build_legal_entity_candidates,
    get_effective_max_websites,
)
from app.rc_matching import build_rc_verification_records
from app.serpapi_client import SerpApiClient


logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO") -> None:
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    run_started_at = datetime.now(timezone.utc).isoformat()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    logger.info("Starting shadow economy activity scraper")
    logger.info("Run ID: %s", run_id)
    logger.info("App mode: %s", settings.app_mode)
    logger.info("Provider: %s", settings.provider)
    logger.info("City: %s", settings.scrape_city)
    logger.info("Categories: %s", settings.scrape_categories)
    logger.info("Max categories: %s", settings.max_categories)
    logger.info("Database path: %s", settings.database_path)
    logger.info("SerpApi max pages: %s", settings.serpapi_max_pages)
    logger.info("Max websites to check: %s", settings.max_websites_to_check)

    if settings.app_mode != "demo" and settings.provider != "serpapi":
        raise NotImplementedError(
            f"Provider '{settings.provider}' is not implemented in main.py yet"
        )

    if settings.app_mode != "demo" and not settings.serpapi_api_key:
        raise ValueError("SERPAPI_API_KEY is missing")

    client: Optional[SerpApiClient] = None

    if settings.app_mode != "demo":
        client = SerpApiClient(
            api_key=settings.serpapi_api_key,
        )

    connection = get_connection(settings.database_path)

    try:
        create_tables(connection)

        insert_pipeline_run(
            connection=connection,
            run_record={
                "run_id": run_id,
                "started_at": run_started_at,
                "run_label": f"{settings.scrape_city}_{run_id}",
                "app_mode": settings.app_mode,
                "scrape_city": settings.scrape_city,
                "scrape_categories": settings.scrape_categories,
            },
        )

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
            try:
                businesses_saved, scores_saved, businesses = process_category_job(
                    settings=settings,
                    client=client,
                    connection=connection,
                    job=job,
                    run_id=run_id,
                )

                total_businesses_saved += businesses_saved
                total_scores_saved += scores_saved

                if settings.app_mode == "demo":
                    logger.info("APP_MODE=demo. Skipping website legal extraction.")
                    legal_candidates = []
                else:
                    max_websites = get_effective_max_websites(
                        settings.max_websites_to_check
                    )

                    legal_candidates = build_legal_entity_candidates(
                        businesses=businesses,
                        scraped_at=datetime.now(timezone.utc).isoformat(),
                        max_websites=max_websites,
                    )

                insert_legal_entity_candidates(
                    connection=connection,
                    candidates=legal_candidates,
                )

                total_legal_candidates_saved += len(legal_candidates)

                logger.info(
                    "Saved category=%s | legal_candidates=%s",
                    job["category_key"],
                    len(legal_candidates),
                )

            except Exception:
                logger.exception("Failed to process category job=%s", job)
                continue

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

    finally:
        connection.close()

    logger.info("Finished scraper")
    logger.info("Total businesses saved: %s", total_businesses_saved)
    logger.info("Total activity scores saved: %s", total_scores_saved)
    logger.info("Total legal candidates saved: %s", total_legal_candidates_saved)
    logger.info(
        "Run `python -m scripts.export_report` to create the final CSV report."
    )


if __name__ == "__main__":
    main()