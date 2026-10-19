SELECT
    match_status,
    match_method,
    COUNT(*) AS row_count
FROM rc_verifications
GROUP BY
    match_status,
    match_method
ORDER BY
    row_count DESC;