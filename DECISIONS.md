# Decisions

## Scope

I built an app with this pipeline:

Google Maps activity → website legal extraction → RC matching → manual-review report.

I did not attempt to prove wrongdoing. The system produces leads for manual review.

## Data sources chosen

### Google Maps via SerpApi

Chosen because Google Maps/local results provide visible business activity signals:
rating, review count, address, website, phone, open state.

Rejected:
- direct Google scraping, because it is fragile and harder to operate ethically
- Google Places API, because it requires billing
- Oxylabs Google Maps, because the endpoint failed during testing

### Registrų centras CSV

Chosen because it provides official legal entity codes and financial statement data.

Rejected:
- Rekvizitai.lt / Info.lt because bulk extraction requires licensing
- Sodra/VMI/VMVT due to time constraints

## Matching approach

Website scraper extracts candidate legal identifiers:
legal name, company code, VAT code.

Company code is treated as strongest match.
Normalized legal-name matching is fallback.

## Scoring

Google activity score uses:
review count, rating, website, phone, address, open state, hours.

Final report flags businesses for manual review based on:
high online activity + weak/missing RC match or weak revenue signal.

## Known limitations

- Business brand names can differ from legal names.
- Website legal details can be missing or outdated.
- RC financial data lags current activity.
- Low revenue signals do not prove wrongdoing.
- Individual activity cases may not match company registers.
- Results are leads, not accusations.

## Monthly runs

The current system stores latest-state tables and should also store monthly snapshots for longitudinal comparison.