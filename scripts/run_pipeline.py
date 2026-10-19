from scripts.import_rc import main as import_rc_main
from app.main import main as app_main
from scripts.export_report import main as export_report_main


def main() -> None:
    print("Step 1/3: Importing RC data...")
    import_rc_main()

    print("Step 2/3: Running main pipeline...")
    app_main()

    print("Step 3/3: Exporting final report...")
    export_report_main()

    print("Pipeline finished successfully.")


if __name__ == "__main__":
    main()