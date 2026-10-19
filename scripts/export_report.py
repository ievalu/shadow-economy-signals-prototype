import csv
import os
from pathlib import Path

from dotenv import load_dotenv

from app.database import get_connection


load_dotenv()


REPORT_COLUMNS = [
    "business_name",
    "category_key",
    "google_rating",
    "google_review_count",
    "open_state",
    "website",
    "google_maps_url",
    "google_place_id",
    "google_activity_score",
    "google_activity_level",
    "google_activity_reasons_json",
    "website_legal_name",
    "website_company_code",
    "website_vat_code",
    "website_confidence",
    "evidence_url",
    "rc_match_status",
    "rc_match_method",
    "rc_ja_kodas",
    "rc_ja_pavadinimas",
    "rc_form_pavadinimas",
    "rc_stat_pavadinimas",
    "rc_latest_revenue",
    "rc_latest_profit",
    "review_flag",
]


def calculate_review_flag(row: dict) -> str:
    google_activity_level = row.get("google_activity_level")
    google_review_count = row.get("google_review_count") or 0
    rc_match_status = row.get("rc_match_status")
    rc_latest_revenue = row.get("rc_latest_revenue")

    if google_activity_level == "high" and rc_match_status != "matched":
        return "high_activity_no_rc_match_manual_review"

    if (
        google_activity_level == "high"
        and rc_match_status == "matched"
        and rc_latest_revenue is None
    ):
        return "high_activity_no_revenue_signal_manual_review"

    if (
        google_activity_level == "high"
        and rc_match_status == "matched"
        and rc_latest_revenue is not None
        and rc_latest_revenue < 10000
    ):
        return "high_activity_low_revenue_signal_manual_review"

    if (
        google_activity_level == "medium"
        and google_review_count >= 100
        and rc_match_status != "matched"
    ):
        return "medium_activity_no_rc_match_manual_review"

    return "lower_priority"


def fetch_report_rows(connection) -> list[dict]:
    rows = connection.execute("""
        SELECT
            b.business_name,
            b.category_key,
            b.google_rating,
            b.google_review_count,
            b.open_state,
            b.website,
            b.google_maps_url,
            b.google_place_id,

            s.google_activity_score,
            s.google_activity_level,
            s.google_activity_reasons_json,

            l.legal_name AS website_legal_name,
            l.company_code AS website_company_code,
            l.vat_code AS website_vat_code,
            l.confidence_level AS website_confidence,
            l.evidence_url,

            r.match_status AS rc_match_status,
            r.match_method AS rc_match_method,
            r.rc_ja_kodas,
            r.rc_ja_pavadinimas,
            r.rc_form_pavadinimas,
            r.rc_stat_pavadinimas,
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
            b.google_review_count DESC
    """).fetchall()

    report_rows = []

    for row in rows:
        row_dict = dict(row)
        row_dict["review_flag"] = calculate_review_flag(row_dict)
        report_rows.append(row_dict)

    return report_rows


def write_csv(rows: list[dict], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=REPORT_COLUMNS,
            extrasaction="ignore",
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(row)


def print_summary(rows: list[dict]) -> None:
    print(f"Exported rows: {len(rows)}")

    review_flag_counts = {}

    for row in rows:
        review_flag = row.get("review_flag")
        review_flag_counts[review_flag] = review_flag_counts.get(review_flag, 0) + 1

    print("Review flag counts:")

    for review_flag, count in sorted(review_flag_counts.items()):
        print(f"  {review_flag}: {count}")

    category_counts = {}

    for row in rows:
        category_key = row.get("category_key")
        category_counts[category_key] = category_counts.get(category_key, 0) + 1

    print("Category counts:")

    for category_key, count in sorted(category_counts.items()):
        print(f"  {category_key}: {count}")


def main() -> None:
    database_path = os.getenv("DATABASE_PATH", "data/shadow_economy.sqlite")
    output_path = os.getenv("REPORT_OUTPUT_PATH", "data/reports/final_report.csv")

    connection = get_connection(database_path)

    rows = fetch_report_rows(connection)

    write_csv(
        rows=rows,
        output_path=output_path,
    )

    connection.close()

    print(f"Exported report to {output_path}")
    print_summary(rows)


if __name__ == "__main__":
    main()