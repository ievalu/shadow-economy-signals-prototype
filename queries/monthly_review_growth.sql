SELECT
    google_place_id,
    business_name,
    category_key,
    MIN(scraped_at) AS first_seen_at,
    MAX(scraped_at) AS last_seen_at,
    MIN(google_review_count) AS first_review_count,
    MAX(google_review_count) AS latest_review_count,
    MAX(google_review_count) - MIN(google_review_count) AS review_count_growth
FROM google_maps_business_snapshots
WHERE google_place_id IS NOT NULL
GROUP BY
    google_place_id,
    business_name,
    category_key
ORDER BY
    review_count_growth DESC;