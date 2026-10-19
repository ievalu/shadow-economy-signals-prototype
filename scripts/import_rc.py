import csv
import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from app.database import (
    create_tables,
    get_connection,
    insert_rc_records,
)
from app.text_utils import fix_mojibake


load_dotenv()


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if value.lower() in ["nan", "none", "null"]:
        return None

    value = fix_mojibake(value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def clean_company_code(value: str | None) -> str | None:
    value = clean_text(value)

    if not value:
        return None

    digits = re.sub(r"[^\d]", "", value)

    if not digits:
        return None

    return digits


def clean_decimal(value: str | None) -> float | None:
    value = clean_text(value)

    if not value:
        return None

    value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return None


def build_hash_key(parts: list[str | None]) -> str:
    raw_key = "|".join(
        part
        for part in parts
        if part
    )

    if not raw_key:
        raw_key = datetime.now(timezone.utc).isoformat()

    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def read_csv_rows(csv_path: str) -> list[dict]:
    encodings_to_try = [
        "utf-8-sig",
        "utf-8",
        "cp1257",
        "latin1",
    ]

    last_error = None

    for encoding in encodings_to_try:
        try:
            with open(csv_path, mode="r", encoding=encoding, newline="") as file:
                sample = file.read(4096)
                file.seek(0)

                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel

                reader = csv.DictReader(file, dialect=dialect)
                rows = list(reader)

                print(f"Read RC CSV using encoding={encoding}")
                print(f"Detected columns: {reader.fieldnames}")

                return rows

        except UnicodeDecodeError as error:
            last_error = error
            continue

    raise UnicodeDecodeError(
        "unknown",
        b"",
        0,
        1,
        f"Could not decode RC CSV file. Last error: {last_error}",
    )


def parse_rc_row(
    row: dict,
    source_file: str,
    imported_at: str,
) -> tuple[dict | None, dict | None]:
    ja_kodas = clean_company_code(row.get("ja_kodas"))
    ja_pavadinimas = clean_text(row.get("ja_pavadinimas"))

    if not ja_kodas:
        return None, None

    form_kodas = clean_text(row.get("form_kodas"))
    form_pavadinimas = clean_text(row.get("form_pavadinimas"))
    stat_kodas = clean_text(row.get("stat_kodas"))
    stat_pavadinimas = clean_text(row.get("stat_pavadinimas"))

    template_id = clean_text(row.get("template_id"))
    template_name = clean_text(row.get("template_name"))
    standard_id = clean_text(row.get("standard_id"))
    standard_name = clean_text(row.get("standard_name"))

    line_type_id = clean_text(row.get("line_type_id"))
    line_name = clean_text(row.get("line_name"))
    reiksme = clean_decimal(row.get("reiksme"))

    beginning_date = clean_text(row.get("beginning_date"))
    turning_date = clean_text(row.get("turning_date"))
    reg_date = clean_text(row.get("reg_date"))
    formavimo_data = clean_text(row.get("formavimo_data"))

    entity_record = {
        "ja_kodas": ja_kodas,
        "ja_pavadinimas": ja_pavadinimas,
        "form_kodas": form_kodas,
        "form_pavadinimas": form_pavadinimas,
        "stat_kodas": stat_kodas,
        "stat_pavadinimas": stat_pavadinimas,
        "latest_reg_date": reg_date,
        "latest_formavimo_data": formavimo_data,
        "source_file": source_file,
        "imported_at": imported_at,
    }

    financial_key = build_hash_key([
        "rc_financial",
        ja_kodas,
        template_id,
        standard_id,
        line_type_id,
        beginning_date,
        turning_date,
        reg_date,
    ])

    financial_record = {
        "source_record_key": financial_key,
        "ja_kodas": ja_kodas,
        "ja_pavadinimas": ja_pavadinimas,
        "form_kodas": form_kodas,
        "form_pavadinimas": form_pavadinimas,
        "stat_kodas": stat_kodas,
        "stat_pavadinimas": stat_pavadinimas,
        "template_id": template_id,
        "template_name": template_name,
        "standard_id": standard_id,
        "standard_name": standard_name,
        "line_type_id": line_type_id,
        "line_name": line_name,
        "reiksme": reiksme,
        "beginning_date": beginning_date,
        "turning_date": turning_date,
        "reg_date": reg_date,
        "formavimo_data": formavimo_data,
        "source_file": source_file,
        "imported_at": imported_at,
    }

    return entity_record, financial_record


def build_rc_records(
    rows: list[dict],
    source_file: str,
    imported_at: str,
) -> tuple[list[dict], list[dict]]:
    entities_by_code = {}
    financial_records = []

    for index, row in enumerate(rows, start=1):
        entity_record, financial_record = parse_rc_row(
            row=row,
            source_file=source_file,
            imported_at=imported_at,
        )

        if entity_record:
            entities_by_code[entity_record["ja_kodas"]] = entity_record

        if financial_record:
            financial_records.append(financial_record)

        if index % 10000 == 0:
            print(f"Parsed {index} RC rows...")

    return list(entities_by_code.values()), financial_records


def import_rc_csv(
    database_path: str,
    csv_path: str,
) -> None:
    if not Path(csv_path).exists():
        raise FileNotFoundError(f"RC CSV file not found: {csv_path}")

    connection = get_connection(database_path)
    create_tables(connection)

    imported_at = datetime.now(timezone.utc).isoformat()

    rows = read_csv_rows(csv_path)

    entity_records, financial_records = build_rc_records(
        rows=rows,
        source_file=csv_path,
        imported_at=imported_at,
    )

    insert_rc_records(
        connection=connection,
        entity_records=entity_records,
        financial_records=financial_records,
    )

    entity_count = connection.execute("""
        SELECT COUNT(*) AS row_count
        FROM rc_entities
    """).fetchone()["row_count"]

    financial_count = connection.execute("""
        SELECT COUNT(*) AS row_count
        FROM rc_financial_records
    """).fetchone()["row_count"]

    print("")
    print(f"Parsed unique RC entities from file: {len(entity_records)}")
    print(f"Parsed RC financial records from file: {len(financial_records)}")
    print(f"Total rows in rc_entities: {entity_count}")
    print(f"Total rows in rc_financial_records: {financial_count}")

    connection.close()


def main() -> None:
    database_path = os.getenv("DATABASE_PATH", "data/shadow_economy.sqlite")
    csv_path = os.getenv("RC_CSV_PATH", "data/raw_external/rc_financials.csv")

    print(f"Database path: {database_path}")
    print(f"RC CSV path: {csv_path}")

    import_rc_csv(
        database_path=database_path,
        csv_path=csv_path,
    )


if __name__ == "__main__":
    main()