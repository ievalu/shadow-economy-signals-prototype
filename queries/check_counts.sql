SELECT 'google_maps_businesses' AS table_name, COUNT(*) AS row_count FROM google_maps_businesses
UNION ALL
SELECT 'google_activity_scores', COUNT(*) FROM google_activity_scores
UNION ALL
SELECT 'legal_entity_candidates', COUNT(*) FROM legal_entity_candidates
UNION ALL
SELECT 'rc_entities', COUNT(*) FROM rc_entities
UNION ALL
SELECT 'rc_financial_records', COUNT(*) FROM rc_financial_records
UNION ALL
SELECT 'rc_verifications', COUNT(*) FROM rc_verifications