import requests


class SerpApiClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("SERPAPI_API_KEY is missing")

        self.api_key = api_key
        self.base_url = "https://serpapi.com/search.json"

    def search_google_maps(
        self,
        query: str,
        latitude: float = 54.6872,
        longitude: float = 25.2797,
        zoom: int = 14,
        language: str = "lt",
        country: str = "lt",
    ) -> dict:
        params = {
            "engine": "google_maps",
            "q": query,
            "ll": f"@{latitude},{longitude},{zoom}z",
            "hl": language,
            "gl": country,
            "api_key": self.api_key,
        }

        return self._get(params)

    def get_next_page(
        self,
        next_url: str,
    ) -> dict:
        response = requests.get(
            next_url,
            params={
                "api_key": self.api_key,
            },
            timeout=60,
        )

        response.raise_for_status()
        return response.json()

    def _get(self, params: dict) -> dict:
        response = requests.get(
            self.base_url,
            params=params,
            timeout=60,
        )

        response.raise_for_status()
        return response.json()


def parse_google_maps_businesses(
    data: dict,
    category_key: str,
    search_query: str,
) -> list[dict]:
    businesses = []

    local_results = data.get("local_results", [])

    for result in local_results:
        business_name = result.get("title")

        if not business_name:
            continue

        businesses.append({
            "business_name": business_name,
            "category_key": category_key,
            "search_query": search_query,
            "google_rating": result.get("rating"),
            "google_review_count": result.get("reviews"),
            "address": result.get("address"),
            "phone": result.get("phone"),
            "website": result.get("website"),
            "business_type": result.get("type"),
            "open_state": result.get("open_state"),
            "hours": result.get("hours"),
            "operating_hours": result.get("operating_hours"),
            "google_place_id": result.get("place_id"),
            "google_data_id": result.get("data_id"),
            "google_maps_url": result.get("link"),
            "gps_coordinates": result.get("gps_coordinates"),
        })

    return businesses