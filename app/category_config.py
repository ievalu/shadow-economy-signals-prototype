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