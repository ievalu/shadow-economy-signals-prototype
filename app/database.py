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
    CREATE TABLE IF NOT EXISTS vmi_entities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_record_key TEXT UNIQUE NOT NULL,
        company_code TEXT,
        vat_code TEXT,
        legal_name TEXT,
        status TEXT,
        address TEXT,
        registration_date TEXT,
        deregistration_date TEXT,
        source_file TEXT,
        source_sheet TEXT,
        imported_at TEXT NOT NULL
    )
""")

    connection.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_vmi_entities_company_code
        ON vmi_entities(company_code)
        WHERE company_code IS NOT NULL
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS vmi_tax_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_record_key TEXT UNIQUE NOT NULL,
            source_type TEXT,
            source_id TEXT,
            source_revision TEXT,
            company_code TEXT,
            taxpayer_internal_id TEXT,
            legal_name TEXT,
            legal_type TEXT,
            county_id TEXT,
            municipality_id TEXT,
            previous_year_amount REAL,
            current_year_amount REAL,
            year INTEGER,
            month INTEGER,
            amount REAL,
            source_updated_at TEXT,
            source_file TEXT,
            imported_at TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS vmi_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_place_id TEXT,
            business_name TEXT NOT NULL,
            website_legal_name TEXT,
            website_company_code TEXT,
            website_vat_code TEXT,
            match_status TEXT NOT NULL,
            match_method TEXT,
            vmi_company_code TEXT,
            vmi_vat_code TEXT,
            vmi_legal_name TEXT,
            vmi_status TEXT,
            vmi_address TEXT,
            checked_at TEXT NOT NULL,
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

    connection.commit()


def serialize_json(value) -> str | None:
    if value is None:
        return None

    return json.dumps(value, ensure_ascii=False)


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
    for business in businesses:
        insert_google_maps_business(connection, business)

    connection.commit()

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
    for score_record in score_records:
        insert_google_activity_score(connection, score_record)

    connection.commit()

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
    for candidate in candidates:
        insert_legal_entity_candidate(connection, candidate)

    connection.commit()

def insert_vmi_entity(
    connection: sqlite3.Connection,
    record: dict,
) -> None:
    connection.execute("""
        INSERT INTO vmi_entities (
            source_record_key,
            company_code,
            vat_code,
            legal_name,
            status,
            address,
            registration_date,
            deregistration_date,
            source_file,
            source_sheet,
            imported_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_record_key) DO UPDATE SET
            company_code = excluded.company_code,
            vat_code = excluded.vat_code,
            legal_name = excluded.legal_name,
            status = excluded.status,
            address = excluded.address,
            registration_date = excluded.registration_date,
            deregistration_date = excluded.deregistration_date,
            source_file = excluded.source_file,
            source_sheet = excluded.source_sheet,
            imported_at = excluded.imported_at
    """, (
        record.get("source_record_key"),
        record.get("company_code"),
        record.get("vat_code"),
        record.get("legal_name"),
        record.get("status"),
        record.get("address"),
        record.get("registration_date"),
        record.get("deregistration_date"),
        record.get("source_file"),
        record.get("source_sheet"),
        record.get("imported_at"),
    ))


def insert_vmi_tax_record(
    connection: sqlite3.Connection,
    record: dict,
) -> None:
    connection.execute("""
        INSERT INTO vmi_tax_records (
            source_record_key,
            source_type,
            source_id,
            source_revision,
            company_code,
            taxpayer_internal_id,
            legal_name,
            legal_type,
            county_id,
            municipality_id,
            previous_year_amount,
            current_year_amount,
            year,
            month,
            amount,
            source_updated_at,
            source_file,
            imported_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_record_key) DO UPDATE SET
            source_type = excluded.source_type,
            source_id = excluded.source_id,
            source_revision = excluded.source_revision,
            company_code = excluded.company_code,
            taxpayer_internal_id = excluded.taxpayer_internal_id,
            legal_name = excluded.legal_name,
            legal_type = excluded.legal_type,
            county_id = excluded.county_id,
            municipality_id = excluded.municipality_id,
            previous_year_amount = excluded.previous_year_amount,
            current_year_amount = excluded.current_year_amount,
            year = excluded.year,
            month = excluded.month,
            amount = excluded.amount,
            source_updated_at = excluded.source_updated_at,
            source_file = excluded.source_file,
            imported_at = excluded.imported_at
    """, (
        record.get("source_record_key"),
        record.get("source_type"),
        record.get("source_id"),
        record.get("source_revision"),
        record.get("company_code"),
        record.get("taxpayer_internal_id"),
        record.get("legal_name"),
        record.get("legal_type"),
        record.get("county_id"),
        record.get("municipality_id"),
        record.get("previous_year_amount"),
        record.get("current_year_amount"),
        record.get("year"),
        record.get("month"),
        record.get("amount"),
        record.get("source_updated_at"),
        record.get("source_file"),
        record.get("imported_at"),
    ))


def insert_vmi_records(
    connection: sqlite3.Connection,
    entity_records: list[dict],
    tax_records: list[dict],
) -> None:
    for record in entity_records:
        insert_vmi_entity(connection, record)

    for record in tax_records:
        insert_vmi_tax_record(connection, record)

    connection.commit()

def insert_vmi_verification(
    connection: sqlite3.Connection,
    record: dict,
) -> None:
    connection.execute("""
        INSERT INTO vmi_verifications (
            google_place_id,
            business_name,
            website_legal_name,
            website_company_code,
            website_vat_code,
            match_status,
            match_method,
            vmi_company_code,
            vmi_vat_code,
            vmi_legal_name,
            vmi_status,
            vmi_address,
            checked_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(google_place_id) DO UPDATE SET
            business_name = excluded.business_name,
            website_legal_name = excluded.website_legal_name,
            website_company_code = excluded.website_company_code,
            website_vat_code = excluded.website_vat_code,
            match_status = excluded.match_status,
            match_method = excluded.match_method,
            vmi_company_code = excluded.vmi_company_code,
            vmi_vat_code = excluded.vmi_vat_code,
            vmi_legal_name = excluded.vmi_legal_name,
            vmi_status = excluded.vmi_status,
            vmi_address = excluded.vmi_address,
            checked_at = excluded.checked_at
    """, (
        record.get("google_place_id"),
        record.get("business_name"),
        record.get("website_legal_name"),
        record.get("website_company_code"),
        record.get("website_vat_code"),
        record.get("match_status"),
        record.get("match_method"),
        record.get("vmi_company_code"),
        record.get("vmi_vat_code"),
        record.get("vmi_legal_name"),
        record.get("vmi_status"),
        record.get("vmi_address"),
        record.get("checked_at"),
    ))


def insert_vmi_verifications(
    connection: sqlite3.Connection,
    records: list[dict],
) -> None:
    for record in records:
        insert_vmi_verification(
            connection=connection,
            record=record,
        )

    connection.commit()

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
    for record in entity_records:
        insert_rc_entity(connection, record)

    for record in financial_records:
        insert_rc_financial_record(connection, record)

    connection.commit()


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
    for record in records:
        insert_rc_verification(connection, record)

    connection.commit()