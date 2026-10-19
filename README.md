Shadow Economy Signal Detection Prototype
This project identifies businesses that appear active online but have weak or incomplete official/legal/financial signals.

It does not prove tax evasion or illegal activity. It only creates a manual-review report.

Pipeline
SerpApi Google Maps
-> Google activity scoring
-> Website legal identifier extraction
-> Registru Centras CSV import
-> Legal entity matching
-> CSV report export

Data sources
SerpApi Google Maps
Collects:

business name
address
website
phone
Google rating
Google review count
open state
opening hours
Google place ID
Business websites
Extracts possible legal identifiers:

legal name
company code
VAT code
The scraper checks pages such as:

/
rekvizitai
kontaktai
privatumo-politika
privacy-policy
terms
Registru Centras CSV
Used for official legal and financial reference data.

Expected columns include:

ja_kodas
ja_pavadinimas
form_pavadinimas
stat_pavadinimas
line_name
reiksme
beginning_date
turning_date
reg_date
formavimo_data
Project structure
app/
main.py
config.py
database.py
serpapi_client.py
website_legal_extractor.py
activity_scoring.py

scripts/
import_rc.py
export_report.py

data/
raw_external/
raw_serpapi/
reports/

Environment variables
Create .env from .env.example.

Example .env values:

PROVIDER=serpapi
SERPAPI_API_KEY=your_key
DATABASE_PATH=data/shadow_economy.sqlite
SCRAPE_CITY=Vilnius
SCRAPE_CATEGORIES=food,beauty,cars
MAX_CATEGORIES=3
MAP_LATITUDE=54.6872
MAP_LONGITUDE=25.2797
MAP_ZOOM=14
MAP_LANGUAGE=lt
MAP_COUNTRY=lt
SERPAPI_MAX_PAGES=2
RC_CSV_PATH=data/raw_external/rc_financials.csv
REPORT_OUTPUT_PATH=data/reports/final_report.csv
LOG_LEVEL=INFO
REQUEST_DELAY_SECONDS=2
DRY_RUN=false

Local run
Install dependencies:

python -m pip install -r requirements.txt

Import RC data:

python -m scripts.import_rc

Run main pipeline:

python -m app.main

Export report:

python -m scripts.export_report

Final report path:

data/reports/final_report.csv

Docker run
Build image:

docker compose build

Import RC data:

docker compose run --rm business_monitor python -m scripts.import_rc

Run pipeline:

docker compose run --rm business_monitor python -m app.main

Export report:

docker compose run --rm business_monitor python -m scripts.export_report

If your Docker service is not called business_monitor, check the service name with:

docker compose config --services

Main database tables
google_maps_businesses
google_activity_scores
legal_entity_candidates
rc_entities
rc_financial_records
rc_verifications
Report columns
The exported CSV includes:

business_name
category_key
google_rating
google_review_count
google_activity_score
google_activity_level
website
website_legal_name
website_company_code
website_vat_code
rc_match_status
rc_match_method
rc_ja_pavadinimas
rc_latest_revenue
rc_latest_profit
review_flag
Review flags
Important values:

high_activity_no_rc_match_manual_review
high_activity_no_revenue_signal_manual_review
high_activity_low_revenue_signal_manual_review
medium_activity_no_rc_match_manual_review
lower_priority
These flags mean the business should be reviewed manually. They are not accusations.

Useful SQL
Check row counts:

SELECT 'google_maps_businesses' AS table_name, COUNT() AS row_count FROM google_maps_businesses
UNION ALL
SELECT 'google_activity_scores', COUNT() FROM google_activity_scores
UNION ALL
SELECT 'legal_entity_candidates', COUNT() FROM legal_entity_candidates
UNION ALL
SELECT 'rc_entities', COUNT() FROM rc_entities
UNION ALL
SELECT 'rc_financial_records', COUNT() FROM rc_financial_records
UNION ALL
SELECT 'rc_verifications', COUNT() FROM rc_verifications;

Check RC matches:

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

Final joined results:

SELECT
b.business_name,
b.category_key,
b.google_rating,
b.google_review_count,
s.google_activity_score,
s.google_activity_level,
l.legal_name AS website_legal_name,
l.company_code AS website_company_code,
r.match_status AS rc_match_status,
r.match_method AS rc_match_method,
r.rc_ja_pavadinimas,
r.rc_latest_revenue,
r.rc_latest_profit
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

Limitations
Google Maps data can be incomplete or outdated.
Business names may differ from legal entity names.
Brands, franchises, and group companies may cause false mismatches.
Website legal details may be missing or outdated.
RC financial data may lag behind current business activity.
Missing or low revenue signals do not prove wrongdoing.
Some businesses may operate legally under individual activity.
Future improvements
Add VMVT matching for food businesses.
Add Sodra employee count data.
Add VMI VAT validation.
Add fuzzy matching.
Add Streamlit dashboard.
Track review-count changes over time.
Disclaimer
This project produces risk signals for manual review. It does not identify confirmed shadow-economy businesses.