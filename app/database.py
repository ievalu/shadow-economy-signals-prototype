import json
import sqlite3
from pathlib import Path


def get_connection(database_path: str) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row

    return connection


def create_tables(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            run_label TEXT,
            app_mode TEXT,
            scrape_city TEXT,
            scrape_categories_json TEXT
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS google_maps_businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            category_key TEXT,
            search_query TEXT,
            google_rating REAL,
            google_review_count INTEGER,
            address TEXT,
            phone TEXT,
            website TEXT,
            business_type TEXT,
            open_state TEXT,
            hours TEXT,
            operating_hours_json TEXT,
            google_place_id TEXT UNIQUE,
            google_data_id TEXT,
            google_maps_url TEXT,
            latitude REAL,
            longitude REAL,
            scraped_at TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS google_maps_business_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            google_place_id TEXT,
            business_name TEXT NOT NULL,
            category_key TEXT,
            search_query TEXT,
            google_rating REAL,
            google_review_count INTEGER,
            address TEXT,
            phone TEXT,
            website TEXT,
            business_type TEXT,
            open_state TEXT,
            hours TEXT,
            operating_hours_json TEXT,
            google_data_id TEXT,
            google_maps_url TEXT,
            latitude REAL,
            longitude REAL,
            scraped_at TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS google_activity_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_place_id TEXT,
            business_name TEXT NOT NULL,
            category_key TEXT,
            google_activity_score INTEGER NOT NULL,
            google_activity_level TEXT NOT NULL,
            google_activity_reasons_json TEXT,
            calculated_at TEXT NOT NULL,
            UNIQUE(google_place_id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS legal_entity_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_place_id TEXT,
            business_name TEXT NOT NULL,
            website TEXT,
            evidence_url TEXT,
            legal_name TEXT,
            legal_form TEXT,
            company_code TEXT,
            vat_code TEXT,
            match_source TEXT,
            confidence_level TEXT,
            checked_pages_json TEXT,
            scraped_at TEXT NOT NULL,
            UNIQUE(google_place_id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS rc_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ja_kodas TEXT UNIQUE NOT NULL,
            ja_pavadinimas TEXT,
            form_kodas TEXT,
            form_pavadinimas TEXT,
            stat_kodas TEXT,
            stat_pavadinimas TEXT,
            latest_reg_date TEXT,
            latest_formavimo_data TEXT,
            source_file TEXT,
            imported_at TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS rc_financial_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_record_key TEXT UNIQUE NOT NULL,
            ja_kodas TEXT NOT NULL,
            ja_pavadinimas TEXT,
            form_kodas TEXT,
            form_pavadinimas TEXT,
            stat_kodas TEXT,
            stat_pavadinimas TEXT,
            template_id TEXT,
            template_name TEXT,
            standard_id TEXT,
            standard_name TEXT,
            line_type_id TEXT,
            line_name TEXT,
            reiksme REAL,
            beginning_date TEXT,
            turning_date TEXT,
            reg_date TEXT,
            formavimo_data TEXT,
            source_file TEXT,
            imported_at TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS rc_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_place_id TEXT,
            business_name TEXT NOT NULL,
            website_legal_name TEXT,
            website_company_code TEXT,
            website_vat_code TEXT,
            match_status TEXT NOT NULL,
            match_method TEXT,
            rc_ja_kodas TEXT,
            rc_ja_pavadinimas TEXT,
            rc_form_pavadinimas TEXT,
            rc_stat_pavadinimas TEXT,
            rc_latest_revenue REAL,
            rc_latest_profit REAL,
            checked_at TEXT NOT NULL,
            UNIQUE(google_place_id)
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_google_maps_businesses_category
        ON google_maps_businesses(category_key)
    """)

    connection.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_google_maps_businesses_name_address_no_place
        ON google_maps_businesses(business_name, address)
        WHERE google_place_id IS NULL
          AND business_name IS NOT NULL
          AND address IS NOT NULL
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_google_maps_snapshots_run_id
        ON google_maps_business_snapshots(run_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_google_maps_snapshots_place_id
        ON google_maps_business_snapshots(google_place_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_google_maps_snapshots_category
        ON google_maps_business_snapshots(category_key)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_legal_entity_candidates_place_id
        ON legal_entity_candidates(google_place_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_legal_entity_candidates_company_code
        ON legal_entity_candidates(company_code)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_rc_entities_name
        ON rc_entities(ja_pavadinimas)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_rc_financial_records_ja_kodas
        ON rc_financial_records(ja_kodas)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_rc_financial_records_line_name
        ON rc_financial_records(line_name)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_rc_verifications_place_id
        ON rc_verifications(google_place_id)
    """)

    connection.commit()


def serialize_json(value) -> str | None:
    if value is None:
        return None

    return json.dumps(value, ensure_ascii=False, default=str)


def insert_pipeline_run(
    connection: sqlite3.Connection,
    run_record: dict,
) -> None:
    connection.execute("""
        INSERT INTO pipeline_runs (
            run_id,
            started_at,
            run_label,
            app_mode,
            scrape_city,
            scrape_categories_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            started_at = excluded.started_at,
            run_label = excluded.run_label,
            app_mode = excluded.app_mode,
            scrape_city = excluded.scrape_city,
            scrape_categories_json = excluded.scrape_categories_json
    """, (
        run_record.get("run_id"),
        run_record.get("started_at"),
        run_record.get("run_label"),
        run_record.get("app_mode"),
        run_record.get("scrape_city"),
        serialize_json(run_record.get("scrape_categories")),
    ))

    connection.commit()


def insert_google_maps_business(
    connection: sqlite3.Connection,
    business: dict,
) -> None:
    gps_coordinates = business.get("gps_coordinates") or {}

    latitude = gps_coordinates.get("latitude")
    longitude = gps_coordinates.get("longitude")

    connection.execute("""
        INSERT INTO google_maps_businesses (
            business_name,
            category_key,
            search_query,
            google_rating,
            google_review_count,
            address,
            phone,
            website,
            business_type,
            open_state,
            hours,
            operating_hours_json,
            google_place_id,
            google_data_id,
            google_maps_url,
            latitude,
            longitude,
            scraped_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(google_place_id) DO UPDATE SET
            business_name = excluded.business_name,
            category_key = excluded.category_key,
            search_query = excluded.search_query,
            google_rating = excluded.google_rating,
            google_review_count = excluded.google_review_count,
            address = excluded.address,
            phone = excluded.phone,
            website = excluded.website,
            business_type = excluded.business_type,
            open_state = excluded.open_state,
            hours = excluded.hours,
            operating_hours_json = excluded.operating_hours_json,
            google_data_id = excluded.google_data_id,
            google_maps_url = excluded.google_maps_url,
            latitude = excluded.latitude,
            longitude = excluded.longitude,
            scraped_at = excluded.scraped_at
    """, (
        business.get("business_name"),
        business.get("category_key"),
        business.get("search_query"),
        business.get("google_rating"),
        business.get("google_review_count"),
        business.get("address"),
        business.get("phone"),
        business.get("website"),
        business.get("business_type"),
        business.get("open_state"),
        business.get("hours"),
        serialize_json(business.get("operating_hours")),
        business.get("google_place_id"),
        business.get("google_data_id"),
        business.get("google_maps_url"),
        latitude,
        longitude,
        business.get("scraped_at"),
    ))


def insert_google_maps_businesses(
    connection: sqlite3.Connection,
    businesses: list[dict],
) -> None:
    try:
        for business in businesses:
            insert_google_maps_business(connection, business)

        connection.commit()

    except Exception:
        connection.rollback()
        raise


def insert_google_maps_business_snapshot(
    connection: sqlite3.Connection,
    run_id: str,
    business: dict,
) -> None:
    gps_coordinates = business.get("gps_coordinates") or {}

    latitude = gps_coordinates.get("latitude")
    longitude = gps_coordinates.get("longitude")

    connection.execute("""
        INSERT INTO google_maps_business_snapshots (
            run_id,
            google_place_id,
            business_name,
            category_key,
            search_query,
            google_rating,
            google_review_count,
            address,
            phone,
            website,
            business_type,
            open_state,
            hours,
            operating_hours_json,
            google_data_id,
            google_maps_url,
            latitude,
            longitude,
            scraped_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        business.get("google_place_id"),
        business.get("business_name"),
        business.get("category_key"),
        business.get("search_query"),
        business.get("google_rating"),
        business.get("google_review_count"),
        business.get("address"),
        business.get("phone"),
        business.get("website"),
        business.get("business_type"),
        business.get("open_state"),
        business.get("hours"),
        serialize_json(business.get("operating_hours")),
        business.get("google_data_id"),
        business.get("google_maps_url"),
        latitude,
        longitude,
        business.get("scraped_at"),
    ))


def insert_google_maps_business_snapshots(
    connection: sqlite3.Connection,
    run_id: str,
    businesses: list[dict],
) -> None:
    try:
        for business in businesses:
            insert_google_maps_business_snapshot(
                connection=connection,
                run_id=run_id,
                business=business,
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise


def insert_google_activity_score(
    connection: sqlite3.Connection,
    score_record: dict,
) -> None:
    connection.execute("""
        INSERT INTO google_activity_scores (
            google_place_id,
            business_name,
            category_key,
            google_activity_score,
            google_activity_level,
            google_activity_reasons_json,
            calculated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(google_place_id) DO UPDATE SET
            business_name = excluded.business_name,
            category_key = excluded.category_key,
            google_activity_score = excluded.google_activity_score,
            google_activity_level = excluded.google_activity_level,
            google_activity_reasons_json = excluded.google_activity_reasons_json,
            calculated_at = excluded.calculated_at
    """, (
        score_record.get("google_place_id"),
        score_record.get("business_name"),
        score_record.get("category_key"),
        score_record.get("google_activity_score"),
        score_record.get("google_activity_level"),
        serialize_json(score_record.get("google_activity_reasons")),
        score_record.get("calculated_at"),
    ))


def insert_google_activity_scores(
    connection: sqlite3.Connection,
    score_records: list[dict],
) -> None:
    try:
        for score_record in score_records:
            insert_google_activity_score(connection, score_record)

        connection.commit()

    except Exception:
        connection.rollback()
        raise


def insert_legal_entity_candidate(
    connection: sqlite3.Connection,
    candidate: dict,
) -> None:
    connection.execute("""
        INSERT INTO legal_entity_candidates (
            google_place_id,
            business_name,
            website,
            evidence_url,
            legal_name,
            legal_form,
            company_code,
            vat_code,
            match_source,
            confidence_level,
            checked_pages_json,
            scraped_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(google_place_id) DO UPDATE SET
            business_name = excluded.business_name,
            website = excluded.website,
            evidence_url = excluded.evidence_url,
            legal_name = excluded.legal_name,
            legal_form = excluded.legal_form,
            company_code = excluded.company_code,
            vat_code = excluded.vat_code,
            match_source = excluded.match_source,
            confidence_level = excluded.confidence_level,
            checked_pages_json = excluded.checked_pages_json,
            scraped_at = excluded.scraped_at
    """, (
        candidate.get("google_place_id"),
        candidate.get("business_name"),
        candidate.get("website"),
        candidate.get("evidence_url"),
        candidate.get("legal_name"),
        candidate.get("legal_form"),
        candidate.get("company_code"),
        candidate.get("vat_code"),
        candidate.get("match_source"),
        candidate.get("confidence_level"),
        serialize_json(candidate.get("checked_pages")),
        candidate.get("scraped_at"),
    ))


def insert_legal_entity_candidates(
    connection: sqlite3.Connection,
    candidates: list[dict],
) -> None:
    try:
        for candidate in candidates:
            insert_legal_entity_candidate(connection, candidate)

        connection.commit()

    except Exception:
        connection.rollback()
        raise


def insert_rc_entity(
    connection: sqlite3.Connection,
    record: dict,
) -> None:
    connection.execute("""
        INSERT INTO rc_entities (
            ja_kodas,
            ja_pavadinimas,
            form_kodas,
            form_pavadinimas,
            stat_kodas,
            stat_pavadinimas,
            latest_reg_date,
            latest_formavimo_data,
            source_file,
            imported_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ja_kodas) DO UPDATE SET
            ja_pavadinimas = excluded.ja_pavadinimas,
            form_kodas = excluded.form_kodas,
            form_pavadinimas = excluded.form_pavadinimas,
            stat_kodas = excluded.stat_kodas,
            stat_pavadinimas = excluded.stat_pavadinimas,
            latest_reg_date = excluded.latest_reg_date,
            latest_formavimo_data = excluded.latest_formavimo_data,
            source_file = excluded.source_file,
            imported_at = excluded.imported_at
    """, (
        record.get("ja_kodas"),
        record.get("ja_pavadinimas"),
        record.get("form_kodas"),
        record.get("form_pavadinimas"),
        record.get("stat_kodas"),
        record.get("stat_pavadinimas"),
        record.get("latest_reg_date"),
        record.get("latest_formavimo_data"),
        record.get("source_file"),
        record.get("imported_at"),
    ))


def insert_rc_financial_record(
    connection: sqlite3.Connection,
    record: dict,
) -> None:
    connection.execute("""
        INSERT INTO rc_financial_records (
            source_record_key,
            ja_kodas,
            ja_pavadinimas,
            form_kodas,
            form_pavadinimas,
            stat_kodas,
            stat_pavadinimas,
            template_id,
            template_name,
            standard_id,
            standard_name,
            line_type_id,
            line_name,
            reiksme,
            beginning_date,
            turning_date,
            reg_date,
            formavimo_data,
            source_file,
            imported_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_record_key) DO UPDATE SET
            ja_kodas = excluded.ja_kodas,
            ja_pavadinimas = excluded.ja_pavadinimas,
            form_kodas = excluded.form_kodas,
            form_pavadinimas = excluded.form_pavadinimas,
            stat_kodas = excluded.stat_kodas,
            stat_pavadinimas = excluded.stat_pavadinimas,
            template_id = excluded.template_id,
            template_name = excluded.template_name,
            standard_id = excluded.standard_id,
            standard_name = excluded.standard_name,
            line_type_id = excluded.line_type_id,
            line_name = excluded.line_name,
            reiksme = excluded.reiksme,
            beginning_date = excluded.beginning_date,
            turning_date = excluded.turning_date,
            reg_date = excluded.reg_date,
            formavimo_data = excluded.formavimo_data,
            source_file = excluded.source_file,
            imported_at = excluded.imported_at
    """, (
        record.get("source_record_key"),
        record.get("ja_kodas"),
        record.get("ja_pavadinimas"),
        record.get("form_kodas"),
        record.get("form_pavadinimas"),
        record.get("stat_kodas"),
        record.get("stat_pavadinimas"),
        record.get("template_id"),
        record.get("template_name"),
        record.get("standard_id"),
        record.get("standard_name"),
        record.get("line_type_id"),
        record.get("line_name"),
        record.get("reiksme"),
        record.get("beginning_date"),
        record.get("turning_date"),
        record.get("reg_date"),
        record.get("formavimo_data"),
        record.get("source_file"),
        record.get("imported_at"),
    ))


def insert_rc_records(
    connection: sqlite3.Connection,
    entity_records: list[dict],
    financial_records: list[dict],
) -> None:
    try:
        for record in entity_records:
            insert_rc_entity(connection, record)

        for record in financial_records:
            insert_rc_financial_record(connection, record)

        connection.commit()

    except Exception:
        connection.rollback()
        raise


def insert_rc_verification(
    connection: sqlite3.Connection,
    record: dict,
) -> None:
    connection.execute("""
        INSERT INTO rc_verifications (
            google_place_id,
            business_name,
            website_legal_name,
            website_company_code,
            website_vat_code,
            match_status,
            match_method,
            rc_ja_kodas,
            rc_ja_pavadinimas,
            rc_form_pavadinimas,
            rc_stat_pavadinimas,
            rc_latest_revenue,
            rc_latest_profit,
            checked_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(google_place_id) DO UPDATE SET
            business_name = excluded.business_name,
            website_legal_name = excluded.website_legal_name,
            website_company_code = excluded.website_company_code,
            website_vat_code = excluded.website_vat_code,
            match_status = excluded.match_status,
            match_method = excluded.match_method,
            rc_ja_kodas = excluded.rc_ja_kodas,
            rc_ja_pavadinimas = excluded.rc_ja_pavadinimas,
            rc_form_pavadinimas = excluded.rc_form_pavadinimas,
            rc_stat_pavadinimas = excluded.rc_stat_pavadinimas,
            rc_latest_revenue = excluded.rc_latest_revenue,
            rc_latest_profit = excluded.rc_latest_profit,
            checked_at = excluded.checked_at
    """, (
        record.get("google_place_id"),
        record.get("business_name"),
        record.get("website_legal_name"),
        record.get("website_company_code"),
        record.get("website_vat_code"),
        record.get("match_status"),
        record.get("match_method"),
        record.get("rc_ja_kodas"),
        record.get("rc_ja_pavadinimas"),
        record.get("rc_form_pavadinimas"),
        record.get("rc_stat_pavadinimas"),
        record.get("rc_latest_revenue"),
        record.get("rc_latest_profit"),
        record.get("checked_at"),
    ))


def insert_rc_verifications(
    connection: sqlite3.Connection,
    records: list[dict],
) -> None:
    try:
        for record in records:
            insert_rc_verification(connection, record)

        connection.commit()

    except Exception:
        connection.rollback()
        raise