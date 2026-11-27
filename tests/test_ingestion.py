"""
CommerceIQ - Automated Data Ingestion Tests
"""

import pytest
import pandas as pd

from src.ingestion.extract import (
    DataIngestionError,
    calculate_file_hash,
    safe_load_csv,
    load_config,
    load_manifest
)


# TC-01: Valid CSV file
def test_valid_csv(tmp_path):

    file_path = tmp_path / "valid.csv"

    file_path.write_text(
        "id,name\n1,Alice\n2,Bob\n",
        encoding="utf-8"
    )

    df = safe_load_csv("valid", file_path)

    assert isinstance(df, pd.DataFrame)
    assert df.shape == (2, 2)
    assert list(df.columns) == ["id", "name"]


# TC-02: Missing file
def test_missing_file(tmp_path):

    file_path = tmp_path / "missing.csv"

    with pytest.raises(
        DataIngestionError,
        match="Source file not found"
    ):
        safe_load_csv("missing", file_path)


# TC-03: Empty file
def test_empty_file(tmp_path):

    file_path = tmp_path / "empty.csv"
    file_path.touch()

    with pytest.raises(
        DataIngestionError,
        match="Source file is empty"
    ):
        safe_load_csv("empty", file_path)


# TC-04: Invalid file extension
def test_invalid_extension(tmp_path):

    file_path = tmp_path / "invalid.txt"

    file_path.write_text(
        "id,name\n1,Alice",
        encoding="utf-8"
    )

    with pytest.raises(
        DataIngestionError,
        match="Invalid file extension"
    ):
        safe_load_csv("invalid", file_path)


# TC-05: Header-only CSV
def test_header_only_csv(tmp_path):

    file_path = tmp_path / "headers.csv"

    file_path.write_text(
        "id,name\n",
        encoding="utf-8"
    )

    with pytest.raises(
        DataIngestionError,
        match="Dataset contains no records"
    ):
        safe_load_csv("headers", file_path)


# TC-06: Malformed CSV
def test_malformed_csv(tmp_path):

    file_path = tmp_path / "malformed.csv"

    file_path.write_text(
        "id,name\n1,Alice\n2,Bob,Extra\n",
        encoding="utf-8"
    )

    with pytest.raises(DataIngestionError):
        safe_load_csv("malformed", file_path)


# TC-07: Correct checksum
def test_correct_checksum(tmp_path):

    file_path = tmp_path / "checksum.csv"

    file_path.write_text(
        "id,name\n1,Alice\n",
        encoding="utf-8"
    )

    expected_hash = calculate_file_hash(file_path)

    df = safe_load_csv(
        "checksum",
        file_path,
        expected_hash=expected_hash
    )

    assert len(df) == 1


# TC-08: Incorrect checksum
def test_incorrect_checksum(tmp_path):

    file_path = tmp_path / "modified.csv"

    file_path.write_text(
        "id,name\n1,Alice\n",
        encoding="utf-8"
    )

    with pytest.raises(
        DataIngestionError,
        match="SHA-256 checksum mismatch"
    ):
        safe_load_csv(
            "modified",
            file_path,
            expected_hash="0" * 64
        )


# TC-09: Preserve leading zeros
def test_preserve_leading_zeros(tmp_path):

    file_path = tmp_path / "zipcodes.csv"

    file_path.write_text(
        "id,zipcode\n001,01234\n",
        encoding="utf-8"
    )

    df = safe_load_csv("zipcodes", file_path)

    assert df.loc[0, "id"] == "001"
    assert df.loc[0, "zipcode"] == "01234"


# TC-10: Preserve empty fields and literal NA
def test_preserve_raw_values(tmp_path):

    file_path = tmp_path / "raw_values.csv"

    file_path.write_text(
        "id,value\n1,\n2,NA\n3,NULL\n",
        encoding="utf-8"
    )

    df = safe_load_csv("raw_values", file_path)

    assert df.loc[0, "value"] == ""
    assert df.loc[1, "value"] == "NA"
    assert df.loc[2, "value"] == "NULL"


# TC-11: Invalid UTF-8 encoding
def test_invalid_encoding(tmp_path):

    file_path = tmp_path / "encoding.csv"

    file_path.write_bytes(
        b"id,name\n1,\xff\n"
    )

    with pytest.raises(DataIngestionError):
        safe_load_csv("encoding", file_path)


# TC-12: Detect file modification
def test_hash_changes_after_modification(tmp_path):

    file_path = tmp_path / "integrity.csv"

    file_path.write_text(
        "id,name\n1,Alice\n",
        encoding="utf-8"
    )

    original_hash = calculate_file_hash(file_path)

    file_path.write_text(
        "id,name\n1,Bob\n",
        encoding="utf-8"
    )

    modified_hash = calculate_file_hash(file_path)

    assert len(original_hash) == 64
    assert len(modified_hash) == 64
    assert original_hash != modified_hash


# TC-13: Project configuration
def test_project_configuration():

    config = load_config()

    assert isinstance(config, dict)
    assert config["project"]["name"] == "CommerceIQ"
    assert config["project"]["currency"] == "BRL"
    assert config["database"]["name"] == "commerceiq"
    assert "metadata" in config["paths"]


# TC-14: Actual dataset manifest
def test_dataset_manifest():

    config = load_config()
    manifest = load_manifest(config)

    assert len(manifest) == 12
    assert manifest["dataset"].is_unique
    assert manifest["status"].eq("PASSED").all()

    assert manifest["sha256"].str.fullmatch(
        r"[0-9a-f]{64}"
    ).all()

    assert manifest["source"].value_counts().to_dict() == {
        "ecommerce": 9,
        "marketing": 2,
        "external": 1
    }