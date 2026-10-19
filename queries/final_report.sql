SELECT
    b.business_name,
    b.category_key,
    b.google_rating,
    b.google_review_count,
    b.open_state,
    b.website,

    s.google_activity_score,
    s.google_activity_level,

    l.legal_name AS website_legal_name,
    l.company_code AS website_company_code,
    l.vat_code AS website_vat_code,
    l.confidence_level AS website_confidence,

    r.match_status AS rc_match_status,
    r.match_method AS rc_match_method,
    r.rc_ja_kodas,
    r.rc_ja_pavadinimas,
    r.rc_form_pavadinimas,
    r.rc_stat_pavadinimas,
    r.rc_latest_revenue,
    r.rc_latest_profit,

    CASE
        WHEN s.google_activity_level = 'high'
             AND (r.match_status IS NULL OR r.match_status != 'matched')
            THEN 'high_activity_no_rc_match_manual_review'

        WHEN s.google_activity_level = 'high'
             AND r.match_status = 'matched'
             AND r.rc_latest_revenue IS NULL
            THEN 'high_activity_no_revenue_signal_manual_review'

        WHEN s.google_activity_level = 'high'
             AND r.match_status = 'matched'
             AND r.rc_latest_revenue < 10000
            THEN 'high_activity_low_revenue_signal_manual_review'

        WHEN s.google_activity_level = 'medium'
             AND b.google_review_count >= 100
             AND (r.match_status IS NULL OR r.match_status != 'matched')
            THEN 'medium_activity_no_rc_match_manual_review'

        ELSE 'lower_priority'
    END AS review_flag

FROM google_maps_businesses AS b
LEFT JOIN google_activity_scores AS s
    ON b.google_place_id = s.google_place_id
LEFT JOIN legal_entity_candidates AS l
    ON b.google_place_id = l.google_place_id
LEFT JOIN rc_verifications AS r
    ON b.google_place_id = r.google_place_id
ORDER BY
    s.google_activity_score DESC,
    b.google_review_count DESC;