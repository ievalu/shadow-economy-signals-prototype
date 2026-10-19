import logging

from app.text_utils import normalize_name


logger = logging.getLogger(__name__)


def load_rc_entities_for_matching(connection) -> list:
    return connection.execute("""
        SELECT
            ja_kodas,
            ja_pavadinimas,
            form_pavadinimas,
            stat_pavadinimas
        FROM rc_entities
        WHERE ja_pavadinimas IS NOT NULL
    """).fetchall()


def find_rc_match(
    connection,
    candidate: dict,
    rc_entities: list,
):
    company_code = candidate.get("company_code")
    legal_name = candidate.get("legal_name")

    if company_code:
        row = connection.execute("""
            SELECT
                ja_kodas,
                ja_pavadinimas,
                form_pavadinimas,
                stat_pavadinimas
            FROM rc_entities
            WHERE ja_kodas = ?
            LIMIT 1
        """, (company_code,)).fetchone()

        if row:
            return "matched", "company_code", row

    if legal_name:
        normalized_candidate_name = normalize_name(legal_name)

        if normalized_candidate_name:
            for row in rc_entities:
                normalized_rc_name = normalize_name(row["ja_pavadinimas"])

                if normalized_rc_name == normalized_candidate_name:
                    return "matched", "legal_name_normalized_exact", row

            for row in rc_entities:
                normalized_rc_name = normalize_name(row["ja_pavadinimas"])

                if not normalized_rc_name:
                    continue

                if (
                    normalized_candidate_name in normalized_rc_name
                    or normalized_rc_name in normalized_candidate_name
                ):
                    return "matched", "legal_name_normalized_partial", row

    return "not_found", None, None


def get_latest_rc_financial_value(
    connection,
    ja_kodas: str,
    line_name_keywords: list[str],
) -> float | None:
    rows = connection.execute("""
        SELECT
            line_name,
            reiksme,
            turning_date,
            reg_date
        FROM rc_financial_records
        WHERE ja_kodas = ?
          AND reiksme IS NOT NULL
        ORDER BY
            turning_date DESC,
            reg_date DESC
    """, (ja_kodas,)).fetchall()

    for row in rows:
        normalized_line_name = normalize_name(row["line_name"])

        if not normalized_line_name:
            continue

        for keyword in line_name_keywords:
            normalized_keyword = normalize_name(keyword)

            if normalized_keyword and normalized_keyword in normalized_line_name:
                return row["reiksme"]

    return None


def build_rc_verification_records(
    connection,
    checked_at: str,
) -> list[dict]:
    candidates = connection.execute("""
        SELECT
            google_place_id,
            business_name,
            legal_name,
            company_code,
            vat_code
        FROM legal_entity_candidates
    """).fetchall()

    rc_entities = load_rc_entities_for_matching(connection)

    records = []

    for candidate_row in candidates:
        candidate = {
            "google_place_id": candidate_row["google_place_id"],
            "business_name": candidate_row["business_name"],
            "legal_name": candidate_row["legal_name"],
            "company_code": candidate_row["company_code"],
            "vat_code": candidate_row["vat_code"],
        }

        match_status, match_method, rc_row = find_rc_match(
            connection=connection,
            candidate=candidate,
            rc_entities=rc_entities,
        )

        rc_latest_revenue = None
        rc_latest_profit_signal = None

        if rc_row:
            rc_latest_revenue = get_latest_rc_financial_value(
                connection=connection,
                ja_kodas=rc_row["ja_kodas"],
                line_name_keywords=[
                    "PARDAVIMO PAJAMOS",
                ],
            )

            rc_latest_profit_signal = get_latest_rc_financial_value(
                connection=connection,
                ja_kodas=rc_row["ja_kodas"],
                line_name_keywords=[
                    "GRYNASIS PELNAS",
                    "ATASKAITINIŲ METŲ PELNAS",
                    "PELNAS PRIEŠ APMOKESTINIMĄ",
                    "PELNAS",
                ],
            )

        records.append({
            "google_place_id": candidate.get("google_place_id"),
            "business_name": candidate.get("business_name"),
            "website_legal_name": candidate.get("legal_name"),
            "website_company_code": candidate.get("company_code"),
            "website_vat_code": candidate.get("vat_code"),
            "match_status": match_status,
            "match_method": match_method,
            "rc_ja_kodas": rc_row["ja_kodas"] if rc_row else None,
            "rc_ja_pavadinimas": rc_row["ja_pavadinimas"] if rc_row else None,
            "rc_form_pavadinimas": rc_row["form_pavadinimas"] if rc_row else None,
            "rc_stat_pavadinimas": rc_row["stat_pavadinimas"] if rc_row else None,
            "rc_latest_revenue": rc_latest_revenue,
            "rc_latest_profit": rc_latest_profit_signal,
            "checked_at": checked_at,
        })

        logger.debug(
            (
                "RC check business=%s | legal_name=%s | company_code=%s | "
                "status=%s | method=%s | rc_name=%s"
            ),
            candidate.get("business_name"),
            candidate.get("legal_name"),
            candidate.get("company_code"),
            match_status,
            match_method,
            rc_row["ja_pavadinimas"] if rc_row else None,
        )

    return records