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

## Registrų centras CSV input

The pipeline expects a Registrų centras financial/legal CSV file.

The full RC CSV is not committed to the repository because it can be large and should be downloaded separately from the official source.

Place the file here:

`data/raw_external/rc_financials.csv`

Then make sure .env contains:

`RC_CSV_PATH=data/raw_external/rc_financials.csv`

The importer is run as part of the full pipeline:

`python -m scripts.run_pipeline`

Or separately:

`python -m scripts.import_rc`

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

## One-command pipeline run

### Local:

`py -m scripts.run_pipeline`

### Docker:

`docker compose up --build`

## Main database tables
- google_maps_businesses
- google_activity_scores
- legal_entity_candidates
- rc_entities
- rc_financial_records
- rc_verifications
- pipeline_runs
- google_maps_business_snapshots

## Monthly snapshots

The app keeps both latest-state tables and historical snapshot tables.

Latest-state tables are upserted:

- google_maps_businesses
- google_activity_scores
- legal_entity_candidates
- rc_verifications

Historical runs are stored in:

- pipeline_runs
- google_maps_business_snapshots

Each pipeline run gets a `run_id`, for example:

20261017T213000Z

This allows analysts to compare Google review counts, ratings, and listing metadata across monthly runs.

## Report columns

The exported CSV includes:

| Column | Meaning |
|---|---|
| business_name | Google Maps business name |
| category_key | Search category, e.g. food, beauty, cars |
| google_rating | Google Maps rating |
| google_review_count | Google Maps review count |
| open_state | Open/closed state at scrape time |
| website | Website from Google Maps |
| google_maps_url | Google Maps listing URL |
| google_place_id | Google Maps identifier for traceability and deduplication |
| google_activity_score | Calculated online activity score |
| google_activity_level | low / medium / high |
| google_activity_reasons_json | Reasons behind the activity score |
| website_legal_name | Legal name extracted from website |
| website_company_code | Company code extracted from website |
| website_vat_code | VAT code extracted from website |
| website_confidence | Confidence of website legal extraction |
| evidence_url | Website page where legal evidence was found |
| rc_match_status | Whether RC match was found |
| rc_match_method | Method used to match to RC |
| rc_ja_kodas | Matched RC entity code |
| rc_ja_pavadinimas | Matched RC entity name |
| rc_form_pavadinimas | RC legal form |
| rc_stat_pavadinimas | RC legal status |
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

## Sample Data and Demo Run

The project includes a small sample dataset so the pipeline can be reviewed without using live API calls or large official files.

Sample files are stored in:

```text
data/sample/
```

Included sample files:

| File | Purpose |
|---|---|
| `sample_google_maps_response.json` | Small SerpApi-like Google Maps response used for demo mode |
| `sample_rc_financials.csv` | Small Registrų centras-like financial dataset for testing the importer |
| `sample_final_report.csv` | Example of the final exported report |

The sample data is intentionally small and is only meant to demonstrate the application flow.

## Demo Mode
Demo mode runs the pipeline using the sample Google Maps response instead of calling SerpApi.

This is useful when:

- no SerpApi API key is available.
- Test the app quickly.
- Review the database/report structure.

Set this in .env:
```
APP_MODE=demo
SAMPLE_GOOGLE_MAPS_PATH=data/sample/sample_google_maps_response.json
RC_CSV_PATH=data/sample/sample_rc_financials.csv
SCRAPE_CATEGORIES=food
MAX_CATEGORIES=1
```
In demo mode, SERPAPI_API_KEY is not required.

## Useful SQL
Useful SQLs are provided under /queries folder.

## Limitations
- Google Maps data can be incomplete or outdated.
- Business names may differ from legal entity names.
- Brands, franchises, and group companies may cause false mismatches.
- Website legal details may be missing or outdated.
- RC financial data may lag behind current business activity.
- Missing or low revenue signals do not prove wrongdoing.
- Some businesses may operate legally under individual activity.
- Historical snapshots allow monthly comparison, but full trend analysis is limited to fields currently snapshotted.
- Google categories and map results depend on location, zoom level, pagination, and SerpApi behavior.

## Future improvements

- Add VMVT matching for food businesses.
- Add Sodra employee count and salary indicators.
- Add licensed business-directory enrichment, e.g. Rekvizitai.lt, if data access is available.
- Track Google review-count changes over time.
- Add a dashboard for manual review and filtering.
- Add automatic official-data refresh: download the latest Registrų centras CSV from the public data endpoint, validate row counts/schema, and import it before each run.