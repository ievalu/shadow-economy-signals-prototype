import os

from dotenv import load_dotenv

from app.main import main as app_main
from scripts.export_report import main as export_report_main
from scripts.import_rc import main as import_rc_main


load_dotenv()


def parse_bool(value: str | None) -> bool:
    if value is None:
        return False

    return value.strip().lower() in ["true", "1", "yes", "y"]


def main() -> None:
    skip_rc_import = parse_bool(os.getenv("SKIP_RC_IMPORT"))

    if skip_rc_import:
        print("Step 1/2: Running main pipeline...")
        app_main()

        print("Step 2/2: Exporting final report...")
        export_report_main()

    else:
        print("Step 1/3: Importing RC data...")
        import_rc_main()

        print("Step 2/3: Running main pipeline...")
        app_main()

        print("Step 3/3: Exporting final report...")
        export_report_main()

    print("Pipeline finished successfully.")


if __name__ == "__main__":
    main()