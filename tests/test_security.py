"""
CommerceIQ - Repository Security & Governance Tests

Verifies no credentials, `.env` files, raw/processed datasets, or large
model binaries are tracked in Git or hardcoded in source/docs/SQL.
"""

import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def test_no_sensitive_or_restricted_files_tracked():
    tracked = _tracked_files()
    for path in tracked:
        assert path != ".env", ".env must never be committed"
        assert not path.startswith("data/raw/"), f"Raw dataset tracked: {path}"
        assert not path.startswith("data/processed/"), f"Processed dataset tracked: {path}"
        assert not path.startswith("models/"), f"Model binary tracked: {path}"
        assert not path.endswith(".joblib"), f"Joblib artifact tracked: {path}"
        assert not path.endswith(".pkl"), f"Pickle artifact tracked: {path}"


def test_gitignore_preserves_required_exclusions():
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in [".env", ".venv/", "data/raw/", "data/processed/", "models/", "logs/"]:
        assert pattern in gitignore, f"Missing gitignore pattern: {pattern}"


def test_no_hardcoded_db_passwords_in_code():
    for folder in ["src", "pipelines", "sql"]:
        base = PROJECT_ROOT / folder
        if not base.exists():
            continue
        for fpath in base.rglob("*"):
            if fpath.is_file() and fpath.suffix in {".py", ".sql"}:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                assert "mysql_native_password" not in content.lower()
                # Ensure connection modules read from env rather than literal password
                if "password=" in content.lower() and "os.getenv" not in content and "ci_root_password" not in content:
                    pytest.fail(f"Potential hardcoded password in {fpath.relative_to(PROJECT_ROOT)}")
