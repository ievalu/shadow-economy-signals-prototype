import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


project_root = Path(__file__).resolve().parents[1]
env_path = project_root / ".env"

load_dotenv(dotenv_path=env_path)


@dataclass
class Settings:
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
    app_mode: str
    sample_google_maps_path: str


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


def get_settings() -> Settings:
    scrape_categories_raw = os.getenv("SCRAPE_CATEGORIES", "food,beauty,cars")

    return Settings(
        provider=os.getenv("PROVIDER", "serpapi"),

        serpapi_api_key=os.getenv("SERPAPI_API_KEY", ""),
        serpapi_max_pages=int(os.getenv("SERPAPI_MAX_PAGES", "1")),

        database_path=os.getenv("DATABASE_PATH", "data/shadow_economy.sqlite"),

        scrape_city=os.getenv("SCRAPE_CITY", "Vilnius"),
        scrape_categories=parse_csv_env(scrape_categories_raw),
        max_categories=int(os.getenv("MAX_CATEGORIES", "3")),

        map_latitude=float(os.getenv("MAP_LATITUDE", "54.6872")),
        map_longitude=float(os.getenv("MAP_LONGITUDE", "25.2797")),
        map_zoom=int(os.getenv("MAP_ZOOM", "14")),
        map_language=os.getenv("MAP_LANGUAGE", "lt"),
        map_country=os.getenv("MAP_COUNTRY", "lt"),

        log_level=os.getenv("LOG_LEVEL", "INFO"),
        request_delay_seconds=int(os.getenv("REQUEST_DELAY_SECONDS", "2")),
        dry_run=parse_bool_env(os.getenv("DRY_RUN"), default=False),
        app_mode=os.getenv("APP_MODE", "live"),
        sample_google_maps_path=os.getenv(
            "SAMPLE_GOOGLE_MAPS_PATH",
            "data/sample/sample_google_maps_response.json",
        )
    )