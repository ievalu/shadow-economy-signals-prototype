# Shadow Economy Signal Detection Prototype
This project identifies businesses that appear active online but have weak or incomplete official/legal/financial signals.

It does not prove tax evasion or illegal activity. It only creates a manual-review report.

## Pipeline
SerpApi Google Maps
-> Google activity scoring
-> Website legal identifier extraction
-> Registrų Centras CSV import
-> Legal entity matching
-> CSV report export|

## Data sources

| Source | Purpose |
|---|---|
| SerpApi Google Maps | Business discovery, Google rating, review count, address, website, phone |
| Business websites | Extract legal name, company code, VAT code |
| Registrų centras CSV | Verify legal entity and financial signals |

The scraper checks pages such as:

/rekvizitai

/kontaktai

/privatumo-politika

/privacy-policy

/terms

## Local run
### Install dependencies:

`py -m pip install -r requirements.txt`

### Import RC data:

`py -m scripts.import_rc`

### Run main pipeline:

`py -m app.main`

### Export report:

`py -m scripts.export_report`

### Final report path:

data/reports/final_report.csv

## Docker run
### Build image:

`docker compose build`

### Import RC data:

`docker compose run --rm business_monitor python -m scripts.import_rc`

### Run pipeline:

`docker compose run --rm business_monitor python -m app.main`

### Export report:

`docker compose run --rm business_monitor python -m scripts.export_report`

## Main database tables
google_maps_businesses
google_activity_scores
legal_entity_candidates
rc_entities
rc_financial_records
rc_verifications

## Report columns
### The exported CSV includes:

| Column | Meaning |
|---|---|
| business_name | Google Maps business name |
| category_key | food, beauty, cars |
| google_rating | Google Maps rating |
| google_review_count | Google Maps review count |
| google_activity_score | Calculated online activity score |
| google_activity_level | low / medium / high |
| website_legal_name | Legal name extracted from website |
| website_company_code | Company code extracted from website |
| rc_match_status | Whether RC match was found |
| rc_match_method | Matching method |
| rc_latest_revenue | Latest revenue signal from RC |
| rc_latest_profit | Latest profit signal from RC |
| review_flag | Manual-review classification |

## Review flags
### Important values:

| Flag | Meaning |
|---|---|
| high_activity_no_rc_match_manual_review | High Google activity but no RC match |
| high_activity_no_revenue_signal_manual_review | High activity, RC matched, but no revenue signal |
| high_activity_low_revenue_signal_manual_review | High activity, RC matched, but low revenue signal |
| medium_activity_no_rc_match_manual_review | Medium activity and no RC match |
| lower_priority | No major mismatch signal |

These flags mean the business should be reviewed manually.

## Useful SQL
Useful SQLs provided under /queries folder.

## Limitations
- Google Maps data can be incomplete or outdated.
- Business names may differ from legal entity names.
- Brands, franchises, and group companies may cause false mismatches.
- Website legal details may be missing or outdated.
- RC financial data may lag behind current business activity.
- Missing or low revenue signals do not prove wrongdoing.
- Some businesses may operate legally under individual activity.

## Future improvements
- Add VMVT matching for food businesses.
- Add Sodra employee count data.
- Track review-count changes over time.