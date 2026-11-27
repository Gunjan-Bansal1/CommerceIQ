"""
CommerceIQ - Data Ingestion Module

Loads registered source datasets, verifies file integrity,
handles ingestion errors and generates execution reports.
"""

import hashlib
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from time import perf_counter

import pandas as pd
import yaml


# --------------------------------------------------
# 1. Project configuration
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config():
    """Load centralized project configuration."""

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("Invalid project configuration.")

    return config


# --------------------------------------------------
# 2. Custom exception
# --------------------------------------------------

class DataIngestionError(Exception):
    """Custom exception for ingestion failures."""

    pass


# --------------------------------------------------
# 3. Logging configuration
# --------------------------------------------------

def configure_logger(config):
    """Configure file and console logging."""

    log_path = (
        PROJECT_ROOT
        / config["paths"]["logs"]
        / "ingestion.log"
    )

    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("commerceiq.ingestion")

    logger.setLevel(config["logging"]["level"])
    logger.propagate = False

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(
        log_path,
        mode="a",
        encoding="utf-8"
    )

    console_handler = logging.StreamHandler(sys.stdout)

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# --------------------------------------------------
# 4. File integrity verification
# --------------------------------------------------

def calculate_file_hash(file_path, chunk_size=1024 * 1024):
    """Calculate the SHA-256 checksum of a file."""

    file_path = Path(file_path)

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:

        for chunk in iter(
            lambda: file.read(chunk_size),
            b""
        ):
            sha256.update(chunk)

    return sha256.hexdigest()


# --------------------------------------------------
# 5. Load and validate dataset manifest
# --------------------------------------------------

def load_manifest(config):
    """Load and validate the registered dataset inventory."""

    manifest_path = (
        PROJECT_ROOT
        / config["paths"]["metadata"]
        / "dataset_manifest.csv"
    )

    if not manifest_path.is_file():
        raise FileNotFoundError("Dataset manifest not found.")

    manifest = pd.read_csv(manifest_path, dtype=str)

    required_columns = {
        "dataset",
        "source",
        "relative_path",
        "sha256",
        "status"
    }

    if not required_columns.issubset(manifest.columns):

        missing = required_columns - set(manifest.columns)

        raise ValueError(
            f"Manifest columns missing: {missing}"
        )

    if len(manifest) != 12:
        raise ValueError("Expected 12 registered datasets.")

    if manifest["dataset"].duplicated().any():
        raise ValueError("Duplicate datasets in manifest.")

    if not manifest["status"].eq("PASSED").all():
        raise ValueError("Manifest contains unvalidated datasets.")

    if not manifest["sha256"].str.fullmatch(
        r"[0-9a-f]{64}"
    ).fillna(False).all():
        raise ValueError("Invalid SHA-256 hashes in manifest.")

    return manifest


# --------------------------------------------------
# 6. Safe CSV ingestion
# --------------------------------------------------

def safe_load_csv(
    dataset_name,
    file_path,
    expected_hash=None,
    logger=None
):
    """Validate and load a source CSV file."""

    file_path = Path(file_path)

    if logger is None:
        logger = logging.getLogger("commerceiq.ingestion")

    try:

        logger.info("Starting ingestion: %s", dataset_name)

        if not file_path.is_file():
            raise FileNotFoundError(
                f"Source file not found: {file_path}"
            )

        if file_path.suffix.lower() != ".csv":
            raise ValueError("Invalid file extension.")

        if file_path.stat().st_size == 0:
            raise ValueError("Source file is empty.")

        if expected_hash is not None:

            actual_hash = calculate_file_hash(file_path)

            if actual_hash != expected_hash:
                raise ValueError("SHA-256 checksum mismatch.")

        start_time = perf_counter()

        df = pd.read_csv(
            file_path,
            encoding="utf-8",
            dtype=str,
            keep_default_na=False,
            low_memory=False,
            on_bad_lines="error"
        )

        if df.empty:
            raise ValueError("Dataset contains no records.")

        logger.info(
            "Loaded: %s | Rows: %d | Columns: %d | Time: %.4f sec",
            dataset_name,
            df.shape[0],
            df.shape[1],
            perf_counter() - start_time
        )

        return df

    except (
        OSError,
        ValueError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError
    ) as error:

        logger.error(
            "Ingestion failed: %s | %s",
            dataset_name,
            error
        )

        raise DataIngestionError(
            f"Unable to ingest {dataset_name}: {error}"
        ) from error


# --------------------------------------------------
# 7. Complete ingestion pipeline
# --------------------------------------------------

def run_ingestion():
    """Load all registered datasets and save ingestion results."""

    config = load_config()
    logger = configure_logger(config)

    pipeline_start = perf_counter()

    logger.info("=" * 60)
    logger.info("CommerceIQ ingestion pipeline started.")

    manifest = load_manifest(config)

    datasets = {}
    ingestion_results = []

    for row in manifest.itertuples(index=False):

        start_time = perf_counter()

        try:

            file_path = (
                PROJECT_ROOT / row.relative_path
            ).resolve()

            raw_root = (PROJECT_ROOT / "data" / "raw").resolve()

            if not file_path.is_relative_to(raw_root):
                raise DataIngestionError(
                    "Source path is outside the raw data directory."
                )

            df = safe_load_csv(
                dataset_name=row.dataset,
                file_path=file_path,
                expected_hash=row.sha256,
                logger=logger
            )

            datasets[row.dataset] = df

            ingestion_results.append({
                "dataset": row.dataset,
                "source": row.source,
                "rows": df.shape[0],
                "columns": df.shape[1],
                "memory_mib": round(
                    df.memory_usage(deep=True).sum()
                    / (1024 ** 2),
                    2
                ),
                "load_time_sec": round(
                    perf_counter() - start_time,
                    4
                ),
                "status": "LOADED",
                "error": None
            })

        except DataIngestionError as error:

            logger.error("%s: %s", row.dataset, error)

            ingestion_results.append({
                "dataset": row.dataset,
                "source": row.source,
                "rows": 0,
                "columns": 0,
                "memory_mib": 0,
                "load_time_sec": round(
                    perf_counter() - start_time,
                    4
                ),
                "status": "FAILED",
                "error": str(error)
            })

    summary = pd.DataFrame(ingestion_results)

    summary["ingested_at_utc"] = datetime.now(
        timezone.utc
    ).isoformat()

    # Save ingestion report
    report_path = (
        PROJECT_ROOT
        / config["paths"]["metadata"]
        / "ingestion_summary.csv"
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)

    summary.to_csv(
        report_path,
        index=False,
        encoding="utf-8"
    )

    successful = int(summary["status"].eq("LOADED").sum())
    failed = int(summary["status"].eq("FAILED").sum())

    print("\nCOMMERCEIQ - INGESTION SUMMARY\n")

    print(
        summary[
            ["dataset", "rows", "columns", "status"]
        ].to_string(index=False)
    )

    print(f"\nTotal datasets : {len(summary)}")
    print(f"Successful     : {successful}")
    print(f"Failed         : {failed}")
    print(f"Total records  : {summary['rows'].sum():,}")
    print(
        f"Execution time : "
        f"{perf_counter() - pipeline_start:.2f} seconds"
    )
    print(
        f"Report saved   : "
        f"{report_path.relative_to(PROJECT_ROOT)}"
    )

    if failed > 0:

        logger.error("Pipeline completed with failures.")

        raise DataIngestionError(
            f"{failed} datasets failed ingestion."
        )

    logger.info("CommerceIQ ingestion completed successfully.")

    return datasets, summary


# --------------------------------------------------
# 8. Script entry point
# --------------------------------------------------

if __name__ == "__main__":

    try:

        datasets, summary = run_ingestion()

    except Exception as error:

        logging.getLogger(
            "commerceiq.ingestion"
        ).exception("Pipeline failed: %s", error)

        sys.exit(1)