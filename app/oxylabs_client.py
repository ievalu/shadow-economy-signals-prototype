import requests


class OxylabsClient:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.base_url = "https://realtime.oxylabs.io/v1/queries"

    def search(self, source: str, query: str, geo_location: str = "Lithuania") -> dict:
        payload = {
            "source": source,
            "query": query,
            "geo_location": geo_location,
            "parse": True,
        }

        response = requests.post(
            self.base_url,
            auth=(self.username, self.password),
            json=payload,
            timeout=60,
        )

        response.raise_for_status()
        return response.json()