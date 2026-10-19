import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


project_root = Path(__file__).resolve().parents[1]
env_path = project_root / ".env"

load_dotenv(dotenv_path=env_path)


@dataclass
class Settings:
    # App mode
    app_mode: str

    # Provider
    provider: str

    # SerpApi
    serpapi_api_key: str
    serpapi_max_pages: int

    # Database
    database_path: str

    # Scraping config
    scrape_city: str
    scrape_categories: list[str]
    max_categories: int
    max_websites_to_check: int

    # Google Maps location config
    map_latitude: float
    map_longitude: float
    map_zoom: int
    map_language: str
    map_country: str

    # Runtime
    log_level: str
    request_delay_seconds: int
    dry_run: bool

    # Demo/sample data
    sample_google_maps_path: str

    # External files / reports
    rc_csv_path: str
    report_output_path: str


def parse_csv_env(value: str) -> list[str]:
    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def parse_bool_env(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default

    return value.strip().lower() in ["true", "1", "yes", "y"]


def parse_int_env(value: str | None, default: int) -> int:
    if value is None or value.strip() == "":
        return default

    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"Invalid integer environment value: {value}") from error


def parse_float_env(value: str | None, default: float) -> float:
    if value is None or value.strip() == "":
        return default

    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"Invalid float environment value: {value}") from error


def normalize_choice(
    value: str,
    allowed_values: set[str],
    field_name: str,
) -> str:
    normalized_value = value.strip().lower()

    if normalized_value not in allowed_values:
        raise ValueError(
            f"Invalid {field_name}: {value}. "
            f"Allowed values: {sorted(allowed_values)}"
        )

    return normalized_value


def get_settings() -> Settings:
    scrape_categories_raw = os.getenv("SCRAPE_CATEGORIES", "food,beauty,cars")

    app_mode = normalize_choice(
        value=os.getenv("APP_MODE", "live"),
        allowed_values={"live", "demo"},
        field_name="APP_MODE",
    )

    provider = normalize_choice(
        value=os.getenv("PROVIDER", "serpapi"),
        allowed_values={"serpapi"},
        field_name="PROVIDER",
    )

    return Settings(
        app_mode=app_mode,

        provider=provider,

        serpapi_api_key=os.getenv("SERPAPI_API_KEY", ""),
        serpapi_max_pages=parse_int_env(
            os.getenv("SERPAPI_MAX_PAGES"),
            default=1,
        ),

        database_path=os.getenv("DATABASE_PATH", "data/shadow_economy.sqlite"),

        scrape_city=os.getenv("SCRAPE_CITY", "Vilnius"),
        scrape_categories=parse_csv_env(scrape_categories_raw),
        max_categories=parse_int_env(
            os.getenv("MAX_CATEGORIES"),
            default=3,
        ),
        max_websites_to_check=parse_int_env(
            os.getenv("MAX_WEBSITES_TO_CHECK"),
            default=30,
        ),

        map_latitude=parse_float_env(
            os.getenv("MAP_LATITUDE"),
            default=54.6872,
        ),
        map_longitude=parse_float_env(
            os.getenv("MAP_LONGITUDE"),
            default=25.2797,
        ),
        map_zoom=parse_int_env(
            os.getenv("MAP_ZOOM"),
            default=14,
        ),
        map_language=os.getenv("MAP_LANGUAGE", "lt"),
        map_country=os.getenv("MAP_COUNTRY", "lt"),

        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        request_delay_seconds=parse_int_env(
            os.getenv("REQUEST_DELAY_SECONDS"),
            default=2,
        ),
        dry_run=parse_bool_env(os.getenv("DRY_RUN"), default=False),

        sample_google_maps_path=os.getenv(
            "SAMPLE_GOOGLE_MAPS_PATH",
            "data/sample/sample_google_maps_response.json",
        ),

        rc_csv_path=os.getenv(
            "RC_CSV_PATH",
            "data/raw_external/rc_financials.csv",
        ),
        report_output_path=os.getenv(
            "REPORT_OUTPUT_PATH",
            "data/reports/final_report.csv",
        ),
    )