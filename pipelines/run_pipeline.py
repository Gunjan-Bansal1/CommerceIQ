"""
CommerceIQ - End-to-End Automated Analytics Pipeline Runner (Phase 15)

Orchestrates all project stages with dependency ordering, structured logging,
stage timing, idempotent reruns, and execution metadata output.

Examples:
    python pipelines/run_pipeline.py --stages validate_sources,ingest,load_db,build_warehouse
    python pipelines/run_pipeline.py --skip-cleaning --train-models
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ALL_STAGES = [
    "validate_sources",
    "ingest",
    "clean",
    "load_db",
    "build_warehouse",
    "sql_analytics",
    "excel",
    "analytics",
    "models",
    "validate",
]


def configure_logger() -> logging.Logger:
    log_path = PROJECT_ROOT / "logs" / "pipeline_automation.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("commerceiq.pipeline")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for h in logger.handlers[:]:
        logger.removeHandler(h)
        h.close()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    sh = logging.StreamHandler(sys.stdout)
    fh.setFormatter(fmt)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def stage_validate_sources() -> dict[str, Any]:
    from src.ingestion.extract import load_config, load_manifest

    cfg = load_config()
    manifest = load_manifest(cfg)
    missing = [r.relative_path for r in manifest.itertuples(index=False) if not (PROJECT_ROOT / r.relative_path).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing registered raw source files: {missing}")
    return {"registered_datasets": len(manifest), "missing_files": 0}


def stage_ingest() -> dict[str, Any]:
    from src.ingestion.extract import run_ingestion

    datasets, summary = run_ingestion()
    return {"loaded_datasets": len(datasets), "total_rows": int(summary["rows"].sum())}


def stage_clean() -> dict[str, Any]:
    from src.transformation.clean import run_cleaning

    res = run_cleaning(export=True)
    return {"cleaned_datasets": len(res["datasets"]), "validations_passed": int(res["validation_results"]["status"].eq("PASS").sum())}


def stage_load_db() -> dict[str, Any]:
    from src.database.load_database import load_operational_database

    res = load_operational_database(truncate_first=True, batch_size=5000)
    return {"tables_loaded": len(res["load_summary"]), "total_rows": int(res["load_summary"]["rows_loaded"].sum())}


def stage_build_warehouse() -> dict[str, Any]:
    from src.warehouse.build_warehouse import build_warehouse

    res = build_warehouse()
    return {"warehouse_tables": len(res["validation"]["table_counts"]), "marts": len(res["validation"]["mart_counts"])}


def stage_sql_analytics() -> dict[str, Any]:
    from src.analytics.run_sql_analytics import run_sql_analytics

    res = run_sql_analytics()
    return {"queries_executed": len(res["summary"])}


def stage_excel() -> dict[str, Any]:
    from src.analytics.build_excel_workbook import build_workbook, configure_logger as xl_logger

    res = build_workbook(xl_logger())
    return {"workbook_path": res["workbook_path"], "pivot_verified": res["pivot_verified"]}


def stage_analytics() -> dict[str, Any]:
    from src.optimization.decision_simulator import run_decision_intelligence

    dec_res = run_decision_intelligence()
    return {"scenarios_generated": len(dec_res["scenarios"])}


def stage_models() -> dict[str, Any]:
    from src.forecasting.demand_forecasting import run_forecasting_pipeline
    from src.forecasting.delivery_risk_model import run_delivery_risk_pipeline

    f_res = run_forecasting_pipeline()
    d_res = run_delivery_risk_pipeline()
    return {
        "forecast_rows": len(f_res["forecast_outputs"]),
        "delivery_risk_best_model": d_res["best_model"],
    }


def stage_validate() -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_ci_synthetic.py", "tests/test_security.py", "-v"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Validation pytest failed:\n{proc.stdout}\n{proc.stderr}")
    return {"pytest_returncode": proc.returncode}


STAGE_REGISTRY: dict[str, Callable[[], dict[str, Any]]] = {
    "validate_sources": stage_validate_sources,
    "ingest": stage_ingest,
    "clean": stage_clean,
    "load_db": stage_load_db,
    "build_warehouse": stage_build_warehouse,
    "sql_analytics": stage_sql_analytics,
    "excel": stage_excel,
    "analytics": stage_analytics,
    "models": stage_models,
    "validate": stage_validate,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CommerceIQ End-to-End Analytics Pipeline Runner")
    parser.add_argument(
        "--stages",
        type=str,
        default="validate_sources,ingest,load_db,build_warehouse,sql_analytics,analytics,validate",
        help=f"Comma-separated list of stages from: {', '.join(ALL_STAGES)} (or 'all').",
    )
    parser.add_argument("--skip-cleaning", action="store_true", help="Skip Phase 4 cleaning stage even when 'all' is requested.")
    parser.add_argument("--train-models", action="store_true", help="Include predictive model training & evaluation stage.")
    parser.add_argument("--dry-run", action="store_true", help="Validate stage plan without executing stages.")
    return parser.parse_args(argv)


def resolve_stages(args: argparse.Namespace) -> list[str]:
    if args.stages.strip().lower() == "all":
        selected = list(ALL_STAGES)
    else:
        selected = [s.strip() for s in args.stages.split(",") if s.strip()]
    unknown = [s for s in selected if s not in STAGE_REGISTRY]
    if unknown:
        raise ValueError(f"Unknown pipeline stages: {unknown}")
    if args.skip_cleaning and "clean" in selected:
        selected.remove("clean")
    if args.train_models and "models" not in selected:
        insert_at = selected.index("validate") if "validate" in selected else len(selected)
        selected.insert(insert_at, "models")
    return selected


def run_pipeline(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    stages = resolve_stages(args)
    logger = configure_logger()
    overall_start = perf_counter()

    logger.info("Pipeline plan: %s (dry_run=%s)", stages, args.dry_run)
    if args.dry_run:
        return {"status": "DRY_RUN", "planned_stages": stages, "results": []}

    stage_records: list[dict[str, Any]] = []
    for stage_name in stages:
        t0 = perf_counter()
        logger.info("Starting stage: %s", stage_name)
        try:
            details = STAGE_REGISTRY[stage_name]()
            elapsed = round(perf_counter() - t0, 3)
            stage_records.append({"stage": stage_name, "status": "SUCCESS", "elapsed_sec": elapsed, "details": details})
            logger.info("Completed stage: %-18s | %.2fs | %s", stage_name, elapsed, details)
        except Exception as exc:
            elapsed = round(perf_counter() - t0, 3)
            stage_records.append({"stage": stage_name, "status": "FAILED", "elapsed_sec": elapsed, "error": str(exc)})
            logger.exception("Stage `%s` failed after %.2fs", stage_name, elapsed)
            summary = {
                "executed_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "FAILED",
                "total_elapsed_sec": round(perf_counter() - overall_start, 3),
                "stages": stage_records,
            }
            (PROJECT_ROOT / "data" / "metadata" / "pipeline_execution_summary.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8"
            )
            raise

    summary = {
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "SUCCESS",
        "total_elapsed_sec": round(perf_counter() - overall_start, 3),
        "stages": stage_records,
    }
    (PROJECT_ROOT / "data" / "metadata" / "pipeline_execution_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    logger.info("Pipeline completed successfully in %.2fs", summary["total_elapsed_sec"])
    return summary


if __name__ == "__main__":
    out = run_pipeline()
    print(json.dumps(out, indent=2))
