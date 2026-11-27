"""
CommerceIQ - Reusable data cleaning pipeline.

Generated from validated notebook transformations
in notebooks/02_data_cleaning.ipynb.

Run from the project root:
    python src/transformation/clean.py

Dependencies:
    pandas, numpy, openpyxl, pyarrow

Raw source data remains unchanged.
"""

import sys
import json
import hashlib

from pathlib import Path

import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def display(*args, **kwargs):
    """Console-compatible replacement for notebook display."""
    pass


def calculate_file_sha256(file_path):

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):

            sha256.update(chunk)

    return sha256.hexdigest()


def get_decimal_spec(series):

    """Determine sufficient precision and scale for Decimal values."""

    values = series.dropna()

    if values.empty:
        return 18, 2

    scale = max(
        2,
        max(
            max(-value.as_tuple().exponent, 0)
            for value in values
        )
    )

    integer_digits = max(
        1,
        max(
            value.adjusted() + 1
            if value != 0 else 1
            for value in values
        )
    )

    precision = max(
        18,
        integer_digits + scale
    )

    if precision > 38:

        raise ValueError(
            "Decimal precision exceeds Decimal128 capacity."
        )

    return precision, scale


def build_arrow_schema(df, dictionary, dataset_name):

    """Build a typed Parquet schema from analytical metadata."""

    fields = []

    dataset_dictionary = (
        dictionary.loc[
            dictionary["dataset"].eq(dataset_name)
        ]
        .set_index("column")
    )

    for column in df.columns:

        analytical_type = dataset_dictionary.loc[
            column, "recommended_dtype"
        ]

        if analytical_type in [
            "STRING", "TEXT", "JSON"
        ]:

            arrow_type = pa.string()

        elif analytical_type == "INTEGER":

            arrow_type = pa.int64()

        elif analytical_type == "FLOAT":

            arrow_type = pa.float64()

        elif analytical_type == "BOOLEAN":

            arrow_type = pa.bool_()

        elif analytical_type == "DATE":

            arrow_type = pa.date32()

        elif analytical_type == "DATETIME":

            arrow_type = pa.timestamp("ns")

        elif analytical_type == "DECIMAL":

            precision, scale = get_decimal_spec(
                df[column]
            )

            arrow_type = pa.decimal128(
                precision,
                scale
            )

        else:

            raise ValueError(
                f"Unsupported type: {analytical_type}"
            )

        fields.append(
            pa.field(column, arrow_type)
        )

    return pa.schema(fields)


def export_processed_datasets(
    datasets,
    dictionary,
    project_root
):

    processed_dir = (
        project_root / "data" / "processed"
    )

    metadata_dir = (
        project_root / "data" / "metadata"
    )

    csv_dir = processed_dir / "csv"
    parquet_dir = processed_dir / "parquet"

    for directory in [
        csv_dir,
        parquet_dir,
        metadata_dir
    ]:

        directory.mkdir(
            parents=True,
            exist_ok=True
        )

    manifest_records = []
    schema_registry = {}

    for dataset_name, df in datasets.items():

        csv_path = csv_dir / f"{dataset_name}.csv"

        parquet_path = (
            parquet_dir / f"{dataset_name}.parquet"
        )

        # ----------------------------------------------------
        # CSV export
        # ----------------------------------------------------

        df.to_csv(
            csv_path,
            index=False,
            encoding="utf-8",
            na_rep=""
        )

        # ----------------------------------------------------
        # Typed Parquet export
        # ----------------------------------------------------

        arrow_schema = build_arrow_schema(
            df,
            dictionary,
            dataset_name
        )

        parquet_input = df.copy()

        for field in arrow_schema:

            if pa.types.is_date32(field.type):

                parquet_input[field.name] = (
                    df[field.name].dt.date
                )

        arrow_table = pa.Table.from_pandas(
            parquet_input,
            schema=arrow_schema,
            preserve_index=False,
            safe=True
        )

        pq.write_table(
            arrow_table,
            parquet_path,
            compression="snappy"
        )

        # ----------------------------------------------------
        # Verify exported Parquet structure and values
        # ----------------------------------------------------

        saved_table = pq.read_table(parquet_path)

        assert saved_table.num_rows == len(df)

        assert saved_table.num_columns == len(df.columns)

        assert saved_table.equals(arrow_table), (
            f"Parquet value reconciliation failed: {dataset_name}"
        )

        # Verify CSV dimensions and column order

        csv_check = pd.read_csv(
            csv_path,
            dtype="string",
            keep_default_na=False,
            encoding="utf-8",
            low_memory=False
        )

        assert csv_check.shape == df.shape

        assert csv_check.columns.tolist() == (
            df.columns.tolist()
        )

        del csv_check
        del saved_table
        del arrow_table
        del parquet_input

        # ----------------------------------------------------
        # Create machine-readable schema
        # ----------------------------------------------------

        dataset_dictionary = (
            dictionary.loc[
                dictionary["dataset"].eq(dataset_name)
            ]
            .set_index("column")
        )

        primary_keys = dataset_dictionary.loc[
            dataset_dictionary[
                "primary_key_component"
            ].eq(True)
        ].index.tolist()

        schema_registry[dataset_name] = {
            "rows": len(df),
            "columns": len(df.columns),
            "primary_key": primary_keys,
            "fields": [
                {
                    "column": column,
                    "analytical_type": str(
                        dataset_dictionary.loc[
                            column,
                            "recommended_dtype"
                        ]
                    ),
                    "pandas_dtype": str(
                        df[column].dtype
                    ),
                    "arrow_dtype": str(
                        arrow_schema.field(column).type
                    ),
                    "has_missing_values": bool(
                        df[column].isna().any()
                    )
                }
                for column in df.columns
            ]
        }

        # ----------------------------------------------------
        # Register both exported files
        # ----------------------------------------------------

        for file_format, file_path in [
            ("CSV", csv_path),
            ("PARQUET", parquet_path)
        ]:

            manifest_records.append({
                "dataset": dataset_name,
                "format": file_format,
                "relative_path": (
                    file_path
                    .relative_to(project_root)
                    .as_posix()
                ),
                "rows": len(df),
                "columns": len(df.columns),
                "size_bytes": file_path.stat().st_size,
                "size_mb": round(
                    file_path.stat().st_size
                    / 1024**2,
                    4
                ),
                "sha256": calculate_file_sha256(
                    file_path
                ),
                "validation_status": "PASS"
            })

        print(
            f"Exported {dataset_name}: "
            f"{len(df):,} rows × {len(df.columns)} columns"
        )

    manifest_df = pd.DataFrame(
        manifest_records
    )

    schema_path = (
        processed_dir / "processed_schema.json"
    )

    with open(
        schema_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            schema_registry,
            file,
            indent=4,
            ensure_ascii=False
        )

    manifest_df.to_csv(
        metadata_dir / "processed_manifest.csv",
        index=False
    )

    return manifest_df, schema_registry


def run_cleaning(export=True, return_audit=False):
    """Execute validated CommerceIQ transformations."""

    # Transformation step 4.1
    # Step 4.1: Initialize cleaning environment

    import sys
    from pathlib import Path
    from datetime import datetime

    import pandas as pd
    import numpy as np


    # Locate project root

    PROJECT_ROOT = next(
        path
        for path in [Path.cwd(), *Path.cwd().parents]
        if (path / "src" / "ingestion" / "extract.py").is_file()
    )

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))


    # Reuse existing ingestion pipeline

    from src.ingestion.extract import run_ingestion

    raw_datasets, ingestion_summary = run_ingestion()


    # Create independent working copies

    cleaned_datasets = {
        dataset_name: df.copy(deep=True)
        for dataset_name, df in raw_datasets.items()
    }


    # Load Phase 3 data quality register

    PROFILING_REPORT_PATH = (
        PROJECT_ROOT
        / "reports"
        / "data_profiling_report.xlsx"
    )

    quality_register_df = pd.read_excel(
        PROFILING_REPORT_PATH,
        sheet_name="Quality Issues",
        engine="openpyxl"
    )


    # Load existing data dictionary

    source_dictionary_df = pd.read_excel(
        PROFILING_REPORT_PATH,
        sheet_name="Data Dictionary",
        engine="openpyxl"
    )


    # Initialize cleaning action log

    cleaning_log = []


    def log_cleaning_action(
        dataset,
        action,
        affected_records,
        rows_before,
        rows_after,
        issue_id=None,
        notes=""
    ):
        """Record a cleaning or transformation action."""

        cleaning_log.append({
            "timestamp": datetime.now().isoformat(
                timespec="seconds"
            ),
            "dataset": dataset,
            "issue_id": issue_id,
            "action": action,
            "affected_records": affected_records,
            "rows_before": rows_before,
            "rows_after": rows_after,
            "rows_removed": rows_before - rows_after,
            "notes": notes
        })


    # Capture baseline dataset dimensions

    cleaning_baseline_df = pd.DataFrame([
        {
            "dataset": dataset_name,
            "original_rows": len(df),
            "original_columns": len(df.columns),
            "working_rows": len(cleaned_datasets[dataset_name]),
            "working_columns": len(
                cleaned_datasets[dataset_name].columns
            )
        }

        for dataset_name, df in raw_datasets.items()
    ])


    # Display initialization summary

    print("COMMERCEIQ - DATA CLEANING ENVIRONMENT")

    print("\nProject root:", PROJECT_ROOT)

    print("Python version:", sys.version.split()[0])

    print("Pandas version:", pd.__version__)

    print("NumPy version:", np.__version__)


    print("\nDATASET CLEANING BASELINE")

    display(cleaning_baseline_df)


    print("\nPHASE 3 QUALITY OBSERVATIONS")

    display(
        quality_register_df["priority"]
        .value_counts()
        .rename_axis("priority")
        .reset_index(name="issue_count")
    )


    print("\nCLEANING INITIALIZATION SUMMARY")

    print("Raw datasets loaded:", len(raw_datasets))

    print("Working datasets created:", len(cleaned_datasets))

    print(
        "Total source records:",
        f"{sum(len(df) for df in raw_datasets.values()):,}"
    )

    print(
        "Source fields documented:",
        len(source_dictionary_df)
    )

    print(
        "Quality observations loaded:",
        len(quality_register_df)
    )

    print(
        "Cleaning actions performed:",
        len(cleaning_log)
    )


    assert len(raw_datasets) == 12

    assert len(cleaned_datasets) == 12

    assert len(source_dictionary_df) == 81

    assert len(quality_register_df) == 43


    print("\nStep 4.1 initialized successfully.")

    # Transformation step 4.2
    # Step 4.2: Column name and missing-value standardization

    import re


    # 1. Define explicit column name corrections

    column_name_overrides = {
        "products": {
            "product_name_lenght": "product_name_length",
            "product_description_lenght": "product_description_length"
        },

        "brazil_holidays": {
            "global": "is_global",
            "fixed": "is_fixed"
        }
    }


    def standardize_column_name(column):
        """Convert column names into snake_case."""

        column = re.sub(
            r"([a-z0-9])([A-Z])",
            r"\1_\2",
            str(column)
        )

        column = re.sub(
            r"[^a-zA-Z0-9]+",
            "_",
            column
        )

        return column.strip("_").lower()


    column_mapping_records = []
    missing_standardization_records = []


    # 2. Standardize all datasets

    for dataset_name, df in cleaned_datasets.items():

        rows_before = len(df)

        rename_mapping = {}

        for column in df.columns:

            new_name = standardize_column_name(column)

            new_name = column_name_overrides.get(
                dataset_name, {}
            ).get(column, new_name)

            rename_mapping[column] = new_name

            column_mapping_records.append({
                "dataset": dataset_name,
                "original_column": column,
                "standardized_column": new_name,
                "renamed": column != new_name
            })

        # Prevent accidental column name collisions
        assert len(set(rename_mapping.values())) == len(df.columns)

        renamed_count = sum(
            old != new
            for old, new in rename_mapping.items()
        )

        df = df.rename(columns=rename_mapping)
        cleaned_datasets[dataset_name] = df

        if renamed_count > 0:

            log_cleaning_action(
                dataset=dataset_name,
                action="Standardized column names",
                affected_records=None,
                rows_before=rows_before,
                rows_after=len(df),
                notes=f"{renamed_count} columns renamed."
            )


        # 3. Standardize blank and whitespace-only values

        dataset_converted_cells = 0

        for column in df.columns:

            series = df[column]

            existing_nulls = int(series.isna().sum())

            empty_mask = series.eq("").fillna(False)

            whitespace_mask = (
                series.str.strip().eq("").fillna(False)
                & series.ne("").fillna(False)
            )

            blank_mask = empty_mask | whitespace_mask

            empty_count = int(empty_mask.sum())

            whitespace_count = int(whitespace_mask.sum())

            converted_count = int(blank_mask.sum())

            if converted_count > 0:

                df[column] = series.mask(blank_mask, pd.NA)

            final_missing = int(df[column].isna().sum())

            dataset_converted_cells += converted_count

            missing_standardization_records.append({
                "dataset": dataset_name,
                "column": column,
                "existing_nulls": existing_nulls,
                "empty_strings_converted": empty_count,
                "whitespace_values_converted": whitespace_count,
                "total_converted": converted_count,
                "final_missing_values": final_missing
            })

        if dataset_converted_cells > 0:

            log_cleaning_action(
                dataset=dataset_name,
                action="Standardized missing-value representation",
                affected_records=None,
                rows_before=rows_before,
                rows_after=len(df),
                notes=(
                    f"{dataset_converted_cells:,} blank cells "
                    "converted to missing values."
                )
            )

        assert len(df) == rows_before


    # 4. Consolidate column name mappings

    column_mapping_df = pd.DataFrame(
        column_mapping_records
    )

    renamed_columns_df = column_mapping_df.loc[
        column_mapping_df["renamed"]
    ].reset_index(drop=True)

    print("COMMERCEIQ - COLUMN NAME STANDARDIZATION")

    display(renamed_columns_df)


    # 5. Update working data dictionary

    cleaning_dictionary_df = source_dictionary_df.merge(
        column_mapping_df[
            [
                "dataset",
                "original_column",
                "standardized_column"
            ]
        ],
        left_on=["dataset", "column"],
        right_on=["dataset", "original_column"],
        how="left",
        validate="one_to_one"
    )

    cleaning_dictionary_df["column"] = (
        cleaning_dictionary_df["standardized_column"]
    )

    cleaning_dictionary_df = cleaning_dictionary_df.drop(
        columns=["standardized_column"]
    )


    # 6. Consolidate missing-value standardization

    missing_standardization_df = pd.DataFrame(
        missing_standardization_records
    )

    print("\nMISSING-VALUE STANDARDIZATION")

    display(
        missing_standardization_df.loc[
            missing_standardization_df["total_converted"].gt(0)
        ]
        .sort_values("total_converted", ascending=False)
        .reset_index(drop=True)
    )


    # 7. Dataset-level summary

    standardization_summary_df = (
        missing_standardization_df
        .groupby("dataset", as_index=False)
        .agg(
            empty_strings_converted=(
                "empty_strings_converted", "sum"
            ),
            whitespace_values_converted=(
                "whitespace_values_converted", "sum"
            ),
            total_converted=("total_converted", "sum"),
            final_missing_values=("final_missing_values", "sum")
        )
        .sort_values("total_converted", ascending=False)
        .reset_index(drop=True)
    )

    print("\nDATASET-LEVEL STANDARDIZATION SUMMARY")

    display(standardization_summary_df)


    # 8. Final reconciliation

    original_rows = sum(
        len(df) for df in raw_datasets.values()
    )

    working_rows = sum(
        len(df) for df in cleaned_datasets.values()
    )

    converted_cells = int(
        missing_standardization_df["total_converted"].sum()
    )

    expected_missing_cells = int(
        source_dictionary_df["total_missing"].sum()
    )

    actual_missing_cells = int(
        missing_standardization_df["final_missing_values"].sum()
    )

    assert original_rows == working_rows

    assert actual_missing_cells == expected_missing_cells

    assert len(cleaning_dictionary_df) == 81


    print("\nSTANDARDIZATION SUMMARY")

    print("Datasets standardized:", len(cleaned_datasets))

    print("Columns processed:", len(column_mapping_df))

    print("Columns renamed:", len(renamed_columns_df))

    print(
        "Empty strings converted:",
        f"{missing_standardization_df['empty_strings_converted'].sum():,}"
    )

    print(
        "Whitespace-only values converted:",
        f"{missing_standardization_df['whitespace_values_converted'].sum():,}"
    )

    print("Total cells converted:", f"{converted_cells:,}")

    print("Expected missing cells:", f"{expected_missing_cells:,}")

    print("Actual missing cells:", f"{actual_missing_cells:,}")

    print("Original rows:", f"{original_rows:,}")

    print("Working rows:", f"{working_rows:,}")

    print("Rows removed:", original_rows - working_rows)

    print("Cleaning actions logged:", len(cleaning_log))

    print("\nStep 4.2 completed successfully.")

    # Transformation step 4.3
    # Step 4.3: Data type conversion

    import json
    from decimal import Decimal, InvalidOperation


    # 1. Define reusable conversion function

    def convert_column_dtype(series, target_dtype):
        """Convert a source column into its recommended analytical type."""

        if target_dtype in {"STRING", "TEXT"}:

            return series.astype("string")

        elif target_dtype == "INTEGER":

            return pd.to_numeric(
                series, errors="raise"
            ).astype("Int64")

        elif target_dtype == "FLOAT":

            return pd.to_numeric(
                series, errors="raise"
            ).astype("Float64")

        elif target_dtype == "DECIMAL":

            def convert_decimal(value):

                if pd.isna(value):
                    return pd.NA

                try:

                    result = Decimal(str(value))

                    if not result.is_finite():
                        raise ValueError(
                            f"Non-finite decimal: {value}"
                        )

                    return result

                except InvalidOperation as exc:

                    raise ValueError(
                        f"Invalid decimal value: {value}"
                    ) from exc

            return series.map(convert_decimal).astype("object")

        elif target_dtype in {"DATE", "DATETIME"}:

            converted = pd.to_datetime(
                series,
                errors="raise",
                format="mixed"
            ).astype("datetime64[ns]")

            if target_dtype == "DATE":
                converted = converted.dt.normalize()

            return converted

        elif target_dtype == "BOOLEAN":

            normalized = (
                series.astype("string")
                .str.strip()
                .str.lower()
            )

            invalid_mask = (
                normalized.notna()
                & ~normalized.isin(["true", "false"])
            )

            if invalid_mask.any():
                raise ValueError("Invalid Boolean values detected.")

            return normalized.map({
                "true": True,
                "false": False
            }).astype("boolean")

        elif target_dtype == "JSON":

            def validate_json(value):

                if pd.isna(value):
                    return pd.NA

                parsed = json.loads(value)

                if not isinstance(parsed, list):
                    raise ValueError("Expected a JSON list.")

                # Retain valid JSON as serialized text
                return json.dumps(
                    parsed,
                    ensure_ascii=False
                )

            return series.map(validate_json).astype("string")

        else:

            raise ValueError(
                f"Unsupported analytical type: {target_dtype}"
            )


    # 2. Convert columns according to the data dictionary

    dtype_conversion_records = []

    for dataset_name, df in cleaned_datasets.items():

        dataset_dictionary = cleaning_dictionary_df.loc[
            cleaning_dictionary_df["dataset"].eq(dataset_name)
        ]

        rows_before = len(df)

        converted_columns = 0

        for field in dataset_dictionary.itertuples(index=False):

            column = field.column
            target_dtype = field.recommended_dtype

            series = df[column]

            original_dtype = str(series.dtype)

            missing_before = int(series.isna().sum())

            try:

                converted = convert_column_dtype(
                    series,
                    target_dtype
                )

            except Exception as exc:

                raise ValueError(
                    f"Conversion failed for "
                    f"{dataset_name}.{column}: {exc}"
                ) from exc

            missing_after = int(converted.isna().sum())

            new_missing_values = missing_after - missing_before

            # Conversion must not silently create missing values
            assert new_missing_values == 0, (
                f"Missing-value count changed in "
                f"{dataset_name}.{column}"
            )

            df[column] = converted

            converted_columns += 1

            dtype_conversion_records.append({
                "dataset": dataset_name,
                "column": column,
                "original_dtype": original_dtype,
                "recommended_dtype": target_dtype,
                "converted_dtype": str(df[column].dtype),
                "total_records": len(df),
                "missing_before": missing_before,
                "missing_after": missing_after,
                "new_missing_values": new_missing_values,
                "status": "SUCCESS"
            })

        assert len(df) == rows_before

        log_cleaning_action(
            dataset=dataset_name,
            action="Applied analytical data types",
            affected_records=None,
            rows_before=rows_before,
            rows_after=len(df),
            notes=f"{converted_columns} columns processed."
        )


    # 3. Consolidate conversion results

    dtype_conversion_df = pd.DataFrame(
        dtype_conversion_records
    )

    print("COMMERCEIQ - DATA TYPE CONVERSION")

    with pd.option_context("display.max_rows", None):

        display(
            dtype_conversion_df[
                [
                    "dataset",
                    "column",
                    "original_dtype",
                    "recommended_dtype",
                    "converted_dtype",
                    "new_missing_values",
                    "status"
                ]
            ]
        )


    # 4. Analytical data type distribution

    dtype_distribution_df = (
        dtype_conversion_df["recommended_dtype"]
        .value_counts()
        .rename_axis("analytical_dtype")
        .reset_index(name="column_count")
    )

    print("\nANALYTICAL DATA TYPE DISTRIBUTION")

    display(dtype_distribution_df)


    # 5. Actual Pandas data type distribution

    pandas_dtype_distribution_df = (
        dtype_conversion_df["converted_dtype"]
        .value_counts()
        .rename_axis("pandas_dtype")
        .reset_index(name="column_count")
    )

    print("\nPANDAS DATA TYPE DISTRIBUTION")

    display(pandas_dtype_distribution_df)


    # 6. Update the working dictionary

    cleaning_dictionary_df = cleaning_dictionary_df.merge(
        dtype_conversion_df[
            ["dataset", "column", "converted_dtype"]
        ],
        on=["dataset", "column"],
        how="left",
        validate="one_to_one"
    )


    # 7. Inspect selected converted values

    print("\nSELECTED CONVERTED VALUE TYPES")

    example_columns = [
        ("customers", "customer_zip_code_prefix"),
        ("order_items", "price"),
        ("payments", "payment_installments"),
        ("orders", "order_purchase_timestamp"),
        ("reviews", "review_score"),
        ("products", "product_weight_g"),
        ("closed_deals", "has_company"),
        ("brazil_holidays", "types")
    ]

    display(pd.DataFrame([
        {
            "dataset": dataset_name,
            "column": column,
            "pandas_dtype": str(
                cleaned_datasets[dataset_name][column].dtype
            ),
            "example_value":
                cleaned_datasets[dataset_name][column]
                .dropna().iloc[0],
            "python_value_type": type(
                cleaned_datasets[dataset_name][column]
                .dropna().iloc[0]
            ).__name__
        }
        for dataset_name, column in example_columns
    ]))


    # 8. Final reconciliation

    total_working_rows = sum(
        len(df) for df in cleaned_datasets.values()
    )

    total_missing_after = sum(
        int(df.isna().sum().sum())
        for df in cleaned_datasets.values()
    )

    assert len(dtype_conversion_df) == 81

    assert total_working_rows == original_rows

    assert total_missing_after == actual_missing_cells

    assert dtype_conversion_df["status"].eq("SUCCESS").all()

    assert dtype_conversion_df["new_missing_values"].eq(0).all()


    print("\nDATA TYPE CONVERSION SUMMARY")

    print("Datasets processed:", len(cleaned_datasets))

    print("Columns processed:", len(dtype_conversion_df))

    print(
        "Successful conversions:",
        dtype_conversion_df["status"].eq("SUCCESS").sum()
    )

    print(
        "New missing values:",
        dtype_conversion_df["new_missing_values"].sum()
    )

    print("Total missing cells:", f"{total_missing_after:,}")

    print("Total working rows:", f"{total_working_rows:,}")

    print("Rows removed:", original_rows - total_working_rows)

    print("Cleaning actions logged:", len(cleaning_log))

    print("\nStep 4.3 completed successfully.")

    # Transformation step 4.4
    # Step 4.4: Duplicate resolution and key preservation

    # 1. Load Phase 3 duplicate and key metadata

    source_duplicate_summary_df = pd.read_excel(
        PROFILING_REPORT_PATH,
        sheet_name="Exact Duplicates",
        engine="openpyxl"
    )

    source_granularity_df = pd.read_excel(
        PROFILING_REPORT_PATH,
        sheet_name="Granularity",
        engine="openpyxl"
    )


    # 2. Remove exact duplicates

    duplicate_resolution_records = []

    for dataset_name, df in cleaned_datasets.items():

        rows_before = len(df)

        duplicate_mask = df.duplicated(keep="first")

        duplicates_detected = int(duplicate_mask.sum())

        source_duplicates = int(
            source_duplicate_summary_df.loc[
                source_duplicate_summary_df["dataset"].eq(
                    dataset_name
                ),
                "exact_duplicate_rows"
            ].iloc[0]
        )

        if duplicates_detected > 0:

            # Only geolocation duplicates are approved for removal
            if dataset_name != "geolocation":

                raise ValueError(
                    f"Unexpected duplicates detected in {dataset_name}. "
                    "Manual review required before removal."
                )

            cleaned_datasets[dataset_name] = (
                df.drop_duplicates(keep="first")
                .reset_index(drop=True)
            )

            log_cleaning_action(
                dataset=dataset_name,
                issue_id="DQ001",
                action="Removed redundant geographic observations",
                affected_records=duplicates_detected,
                rows_before=rows_before,
                rows_after=len(cleaned_datasets[dataset_name]),
                notes=(
                    "Retained the first occurrence of each "
                    "identical geographic observation."
                )
            )

        rows_after = len(cleaned_datasets[dataset_name])

        duplicate_resolution_records.append({
            "dataset": dataset_name,
            "rows_before": rows_before,
            "phase3_exact_duplicates": source_duplicates,
            "duplicates_detected": duplicates_detected,
            "duplicates_removed": rows_before - rows_after,
            "rows_after": rows_after,
            "remaining_exact_duplicates": int(
                cleaned_datasets[dataset_name]
                .duplicated().sum()
            ),
            "removal_pct": round(
                (rows_before - rows_after) / rows_before * 100,
                4
            )
        })


    duplicate_resolution_df = pd.DataFrame(
        duplicate_resolution_records
    )

    print("COMMERCEIQ - DUPLICATE RESOLUTION")

    display(duplicate_resolution_df)


    # 3. Validate primary keys using standardized column names

    primary_key_validation_records = []

    for dataset_name, df in cleaned_datasets.items():

        key_fields = cleaning_dictionary_df.loc[
            cleaning_dictionary_df["dataset"].eq(dataset_name)
            & cleaning_dictionary_df["primary_key_component"].eq(True),
            "column"
        ].tolist()

        if not key_fields:

            primary_key_validation_records.append({
                "dataset": dataset_name,
                "primary_key": "Pending geographic lookup design",
                "total_rows": len(df),
                "missing_key_rows": None,
                "duplicate_key_rows": None,
                "status": "DESIGN PENDING"
            })

            continue

        missing_key_rows = int(
            df[key_fields].isna().any(axis=1).sum()
        )

        duplicate_key_rows = int(
            df.duplicated(subset=key_fields).sum()
        )

        status = (
            "VALID"
            if missing_key_rows == 0
            and duplicate_key_rows == 0
            else "INVALID"
        )

        primary_key_validation_records.append({
            "dataset": dataset_name,
            "primary_key": " + ".join(key_fields),
            "total_rows": len(df),
            "missing_key_rows": missing_key_rows,
            "duplicate_key_rows": duplicate_key_rows,
            "status": status
        })


    primary_key_validation_df = pd.DataFrame(
        primary_key_validation_records
    )

    print("\nPRIMARY KEY VALIDATION AFTER CLEANING")

    display(primary_key_validation_df)


    # 4. Confirm legitimate repeated identifiers are preserved

    preservation_checks = [
        ("customers", "customer_unique_id"),
        ("reviews", "review_id"),
        ("reviews", "order_id")
    ]

    preservation_records = []

    for dataset_name, column in preservation_checks:

        original_repetitions = int(
            raw_datasets[dataset_name][column]
            .duplicated().sum()
        )

        remaining_repetitions = int(
            cleaned_datasets[dataset_name][column]
            .duplicated().sum()
        )

        preserved = original_repetitions == remaining_repetitions

        preservation_records.append({
            "dataset": dataset_name,
            "column": column,
            "original_repeated_values": original_repetitions,
            "remaining_repeated_values": remaining_repetitions,
            "status": "PRESERVED" if preserved else "CHANGED"
        })


    duplicate_preservation_df = pd.DataFrame(
        preservation_records
    )

    print("\nLEGITIMATE REPETITION PRESERVATION")

    display(duplicate_preservation_df)


    # 5. Final reconciliation

    total_rows_before = int(
        duplicate_resolution_df["rows_before"].sum()
    )

    total_rows_removed = int(
        duplicate_resolution_df["duplicates_removed"].sum()
    )

    total_rows_after = sum(
        len(df) for df in cleaned_datasets.values()
    )

    remaining_duplicates = int(
        duplicate_resolution_df[
            "remaining_exact_duplicates"
        ].sum()
    )

    valid_primary_keys = int(
        primary_key_validation_df["status"].eq("VALID").sum()
    )

    invalid_primary_keys = int(
        primary_key_validation_df["status"].eq("INVALID").sum()
    )


    assert total_rows_before - total_rows_removed == total_rows_after

    assert remaining_duplicates == 0

    assert valid_primary_keys == 11

    assert invalid_primary_keys == 0

    assert duplicate_preservation_df["status"].eq(
        "PRESERVED"
    ).all()


    # Confirm transactional datasets have not lost records

    for dataset_name in cleaned_datasets:

        if dataset_name != "geolocation":

            assert len(cleaned_datasets[dataset_name]) == len(
                raw_datasets[dataset_name]
            )


    print("\nDUPLICATE RESOLUTION SUMMARY")

    print("Datasets processed:", len(cleaned_datasets))

    print("Rows before cleaning:", f"{total_rows_before:,}")

    print("Exact duplicates removed:", f"{total_rows_removed:,}")

    print("Rows after cleaning:", f"{total_rows_after:,}")

    print("Remaining exact duplicates:", remaining_duplicates)

    print("Valid primary keys:", valid_primary_keys)

    print("Invalid primary keys:", invalid_primary_keys)

    print(
        "Datasets awaiting key design:",
        primary_key_validation_df["status"].eq(
            "DESIGN PENDING"
        ).sum()
    )

    print(
        "Geolocation records remaining:",
        f"{len(cleaned_datasets['geolocation']):,}"
    )

    print("Cleaning actions logged:", len(cleaning_log))

    print("\nStep 4.4 completed successfully.")

    # Transformation step 4.5
    # Step 4.5: Business-specific missing-value treatment

    # 1. Capture missing-value baseline

    missing_before_df = pd.DataFrame([
        {
            "dataset": dataset_name,
            "column": column,
            "missing_before": int(df[column].isna().sum())
        }
        for dataset_name, df in cleaned_datasets.items()
        for column in df.columns
    ])

    rows_before_treatment = sum(
        len(df) for df in cleaned_datasets.values()
    )

    missing_treatment_records = []


    # 2. Define approved categorical replacements

    fill_rules = {
        ("products", "product_category_name"): {
            "replacement": "unknown",
            "issue_id": "DQ006",
            "reason": "Retain products without recorded categories."
        },

        ("marketing_leads", "origin"): {
            "replacement": "not_recorded",
            "issue_id": "DQ031",
            "reason": "Distinguish missing origin from source-defined unknown."
        }
    }


    # 3. Apply categorical missing-value treatments

    for (dataset_name, column), rule in fill_rules.items():

        df = cleaned_datasets[dataset_name]

        missing_count = int(df[column].isna().sum())

        df[column] = df[column].fillna(
            rule["replacement"]
        )

        missing_treatment_records.append({
            "dataset": dataset_name,
            "column": column,
            "missing_before": missing_count,
            "treatment": "Categorical replacement",
            "replacement": rule["replacement"],
            "missing_after": int(df[column].isna().sum()),
            "reason": rule["reason"]
        })

        log_cleaning_action(
            dataset=dataset_name,
            issue_id=rule["issue_id"],
            action=f"Filled missing {column}",
            affected_records=missing_count,
            rows_before=len(df),
            rows_after=len(df),
            notes=rule["reason"]
        )


    # 4. Remove completely empty holiday metadata

    holiday_df = cleaned_datasets["brazil_holidays"]

    launch_year_missing = int(
        holiday_df["launch_year"].isna().sum()
    )

    # Remove only if the column is completely empty
    assert holiday_df["launch_year"].isna().all()

    cleaned_datasets["brazil_holidays"] = holiday_df.drop(
        columns=["launch_year"]
    )

    missing_treatment_records.append({
        "dataset": "brazil_holidays",
        "column": "launch_year",
        "missing_before": launch_year_missing,
        "treatment": "Column removed",
        "replacement": None,
        "missing_after": None,
        "reason": "Completely empty metadata with no analytical value."
    })

    log_cleaning_action(
        dataset="brazil_holidays",
        issue_id="DQ040",
        action="Removed completely empty launch_year column",
        affected_records=launch_year_missing,
        rows_before=len(holiday_df),
        rows_after=len(cleaned_datasets["brazil_holidays"]),
        notes="Original column remains available in raw source data."
    )


    # 5. Update working data dictionary

    cleaning_dictionary_df = cleaning_dictionary_df.loc[
        ~(
            cleaning_dictionary_df["dataset"].eq("brazil_holidays")
            & cleaning_dictionary_df["column"].eq("launch_year")
        )
    ].reset_index(drop=True)


    # 6. Document intentional missing-value preservation

    preservation_reasons = {
        "orders": (
            "Preserve unavailable lifecycle timestamps; "
            "exclude from relevant duration calculations."
        ),

        "reviews": (
            "Written feedback is optional; preserve missing text."
        ),

        "products": (
            "Avoid unsupported imputation of product attributes."
        ),

        "closed_deals": (
            "Preserve unavailable seller declarations and "
            "unknown Boolean indicators."
        ),

        "brazil_holidays": (
            "Regional subdivision information may not apply "
            "to nationwide holidays."
        )
    }

    for dataset_name, df in cleaned_datasets.items():

        missing_counts = df.isna().sum()

        for column, count in missing_counts.items():

            if count > 0:

                missing_treatment_records.append({
                    "dataset": dataset_name,
                    "column": column,
                    "missing_before": int(count),
                    "treatment": "Preserved",
                    "replacement": None,
                    "missing_after": int(count),
                    "reason": preservation_reasons.get(
                        dataset_name,
                        "Preserve unavailable source information."
                    )
                })


    missing_treatment_df = pd.DataFrame(
        missing_treatment_records
    )

    print("COMMERCEIQ - MISSING-VALUE TREATMENT")

    with pd.option_context("display.max_rows", None):
        display(missing_treatment_df)


    # 7. Dataset-level missing-value reconciliation

    missing_reconciliation_records = []

    for dataset_name, df in cleaned_datasets.items():

        before = int(
            missing_before_df.loc[
                missing_before_df["dataset"].eq(dataset_name),
                "missing_before"
            ].sum()
        )

        after = int(df.isna().sum().sum())

        missing_reconciliation_records.append({
            "dataset": dataset_name,
            "missing_before": before,
            "missing_after": after,
            "missing_cells_reduced": before - after,
            "remaining_columns": len(df.columns),
            "remaining_rows": len(df)
        })


    missing_reconciliation_df = pd.DataFrame(
        missing_reconciliation_records
    )

    print("\nMISSING-VALUE RECONCILIATION")

    display(
        missing_reconciliation_df.sort_values(
            "missing_cells_reduced",
            ascending=False
        )
    )


    # 8. Validate categorical replacements

    print("\nPRODUCT CATEGORY TREATMENT")

    print(
        "Unknown product categories:",
        int(
            cleaned_datasets["products"]["product_category_name"]
            .eq("unknown").sum()
        )
    )

    print("\nMARKETING ORIGIN TREATMENT")

    display(
        cleaned_datasets["marketing_leads"]["origin"]
        .value_counts(dropna=False)
        .rename_axis("origin")
        .reset_index(name="lead_count")
    )


    # 9. Final validation

    total_missing_before = int(
        missing_reconciliation_df["missing_before"].sum()
    )

    total_missing_after = int(
        missing_reconciliation_df["missing_after"].sum()
    )

    total_filled = int(
        missing_treatment_df.loc[
            missing_treatment_df["treatment"].eq(
                "Categorical replacement"
            ),
            "missing_before"
        ].sum()
    )

    total_removed_missing = launch_year_missing

    total_rows_after_treatment = sum(
        len(df) for df in cleaned_datasets.values()
    )

    remaining_fields = sum(
        len(df.columns)
        for df in cleaned_datasets.values()
    )

    assert total_rows_after_treatment == rows_before_treatment

    assert total_missing_after == (
        total_missing_before
        - total_filled
        - total_removed_missing
    )

    assert remaining_fields == 80

    assert len(cleaning_dictionary_df) == remaining_fields

    assert cleaned_datasets["products"][
        "product_category_name"
    ].notna().all()

    assert cleaned_datasets["marketing_leads"][
        "origin"
    ].notna().all()


    print("\nMISSING-VALUE TREATMENT SUMMARY")

    print("Datasets processed:", len(cleaned_datasets))

    print("Missing cells before:", f"{total_missing_before:,}")

    print("Missing cells filled:", f"{total_filled:,}")

    print("Missing cells removed with column:",
          total_removed_missing)

    print("Missing cells intentionally retained:",
          f"{total_missing_after:,}")

    print("Columns removed:", 81 - remaining_fields)

    print("Remaining fields:", remaining_fields)

    print("Total working rows:",
          f"{total_rows_after_treatment:,}")

    print("Rows removed:",
          rows_before_treatment - total_rows_after_treatment)

    print("Cleaning actions logged:", len(cleaning_log))

    print("\nStep 4.5 completed successfully.")

    # Transformation step 4.6
    # Step 4.6: Categorical and text standardization

    import unicodedata


    # 1. Define reusable text normalization functions

    def normalize_city(value):
        """Normalize geographic text while preserving missing values."""

        if pd.isna(value):
            return pd.NA

        value = str(value).strip().casefold()

        value = unicodedata.normalize("NFKD", value)

        value = "".join(
            character
            for character in value
            if not unicodedata.combining(character)
        )

        return " ".join(value.split())


    def normalize_category(series):
        """Standardize categorical labels."""

        return (
            series.str.strip()
            .str.lower()
            .str.replace(r"\s+", " ", regex=True)
        )


    # 2. Define fields requiring standardization

    city_fields = [
        ("customers", "customer_city"),
        ("sellers", "seller_city"),
        ("geolocation", "geolocation_city")
    ]

    state_fields = [
        ("customers", "customer_state"),
        ("sellers", "seller_state"),
        ("geolocation", "geolocation_state")
    ]

    category_fields = [
        ("orders", "order_status"),
        ("payments", "payment_type"),
        ("products", "product_category_name"),
        ("category_translation", "product_category_name"),
        ("category_translation", "product_category_name_english"),
        ("marketing_leads", "origin"),
        ("closed_deals", "business_segment"),
        ("closed_deals", "lead_type"),
        ("closed_deals", "lead_behaviour_profile"),
        ("closed_deals", "average_stock"),
        ("closed_deals", "business_type")
    ]

    review_text_fields = [
        ("reviews", "review_comment_title"),
        ("reviews", "review_comment_message")
    ]


    # 3. Initialize standardization audit

    text_standardization_records = []

    rows_before_text = sum(
        len(df) for df in cleaned_datasets.values()
    )

    missing_before_text = sum(
        int(df.isna().sum().sum())
        for df in cleaned_datasets.values()
    )


    def apply_text_standardization(
        dataset_name,
        column,
        transformed,
        treatment,
        issue_id=None
    ):
        """Apply and document a text transformation."""

        df = cleaned_datasets[dataset_name]

        original = df[column]

        transformed = transformed.astype("string")

        changed_mask = (
            original.notna()
            & transformed.notna()
            & original.ne(transformed).fillna(False)
        )

        changed_count = int(changed_mask.sum())

        unique_before = original.nunique()

        unique_after = transformed.nunique()

        # Ensure no missing information is lost or introduced
        assert original.isna().equals(transformed.isna())

        df[column] = transformed

        text_standardization_records.append({
            "dataset": dataset_name,
            "column": column,
            "treatment": treatment,
            "unique_before": unique_before,
            "unique_after": unique_after,
            "records_changed": changed_count,
            "missing_values": int(transformed.isna().sum())
        })

        if changed_count > 0:

            log_cleaning_action(
                dataset=dataset_name,
                issue_id=issue_id,
                action=f"Standardized {column}",
                affected_records=changed_count,
                rows_before=len(df),
                rows_after=len(df),
                notes=treatment
            )


    # 4. Normalize geographic city names

    city_issue_mapping = {
        "geolocation": "DQ004",
        "sellers": "DQ005"
    }

    for dataset_name, column in city_fields:

        series = cleaned_datasets[dataset_name][column]

        # Normalize distinct labels once for better performance
        city_mapping = {
            value: normalize_city(value)
            for value in series.dropna().unique()
        }

        transformed = series.map(city_mapping)

        apply_text_standardization(
            dataset_name,
            column,
            transformed,
            "Lowercase, Unicode accent and whitespace normalization",
            city_issue_mapping.get(dataset_name)
        )


    # 5. Standardize state abbreviations

    for dataset_name, column in state_fields:

        series = cleaned_datasets[dataset_name][column]

        transformed = series.str.strip().str.upper()

        apply_text_standardization(
            dataset_name,
            column,
            transformed,
            "Uppercase state abbreviation and whitespace trimming"
        )


    # 6. Standardize business categories

    for dataset_name, column in category_fields:

        series = cleaned_datasets[dataset_name][column]

        transformed = normalize_category(series)

        apply_text_standardization(
            dataset_name,
            column,
            transformed,
            "Lowercase and whitespace normalization"
        )


    # 7. Clean surrounding whitespace in review text

    for dataset_name, column in review_text_fields:

        series = cleaned_datasets[dataset_name][column]

        transformed = series.str.strip()

        apply_text_standardization(
            dataset_name,
            column,
            transformed,
            "Trim surrounding whitespace; preserve original content"
        )


    # 8. Consolidate text standardization results

    text_standardization_df = pd.DataFrame(
        text_standardization_records
    )

    print("COMMERCEIQ - CATEGORICAL AND TEXT STANDARDIZATION")

    display(text_standardization_df)


    print("\nFIELDS WITH MODIFIED VALUES")

    display(
        text_standardization_df.loc[
            text_standardization_df["records_changed"].gt(0)
        ].reset_index(drop=True)
    )


    # 9. Resolve missing English category translations

    translation_df = cleaned_datasets["category_translation"]

    products_df = cleaned_datasets["products"]

    product_categories = set(
        products_df["product_category_name"].dropna().unique()
    )

    available_translations = set(
        translation_df["product_category_name"].dropna().unique()
    )

    untranslated_categories = (
        product_categories - available_translations
    )

    manual_translation_mapping = {
        "pc_gamer": "gaming_pc",

        "portateis_cozinha_e_preparadores_de_alimentos":
            "portable_kitchen_and_food_preparation_appliances",

        "unknown": "unknown"
    }

    # Do not silently assign unsupported translations
    assert untranslated_categories.issubset(
        manual_translation_mapping.keys()
    )

    translation_additions_df = pd.DataFrame([
        {
            "product_category_name": category,
            "product_category_name_english":
                manual_translation_mapping[category]
        }
        for category in sorted(untranslated_categories)
    ]).astype("string")


    translation_rows_before = len(translation_df)

    cleaned_datasets["category_translation"] = pd.concat(
        [translation_df, translation_additions_df],
        ignore_index=True
    )

    translation_rows_after = len(
        cleaned_datasets["category_translation"]
    )


    if len(translation_additions_df) > 0:

        log_cleaning_action(
            dataset="category_translation",
            issue_id="DQ007",
            action="Added missing English category mappings",
            affected_records=len(translation_additions_df),
            rows_before=translation_rows_before,
            rows_after=translation_rows_after,
            notes=(
                "Two project-defined translations and one "
                "unknown-category reporting mapping."
            )
        )


    print("\nADDITIONAL CATEGORY TRANSLATIONS")

    display(translation_additions_df)


    # 10. Validate complete product category coverage

    final_translation_df = cleaned_datasets[
        "category_translation"
    ]

    assert final_translation_df[
        "product_category_name"
    ].is_unique

    assert final_translation_df[
        "product_category_name"
    ].notna().all()

    assert final_translation_df[
        "product_category_name_english"
    ].notna().all()

    matched_category_mask = products_df[
        "product_category_name"
    ].isin(
        final_translation_df["product_category_name"]
    )

    matched_products = int(matched_category_mask.sum())

    unmatched_products = int((~matched_category_mask).sum())

    category_coverage_pct = round(
        matched_products / len(products_df) * 100,
        4
    )

    category_translation_summary_df = pd.DataFrame([{
        "total_products": len(products_df),
        "distinct_product_categories": len(product_categories),
        "original_translation_records": translation_rows_before,
        "new_translation_records": len(translation_additions_df),
        "final_translation_records": translation_rows_after,
        "matched_products": matched_products,
        "unmatched_products": unmatched_products,
        "coverage_pct": category_coverage_pct
    }])

    print("\nPRODUCT CATEGORY COVERAGE")

    display(category_translation_summary_df)


    # 11. Validate record and missing-value reconciliation

    rows_after_text = sum(
        len(df) for df in cleaned_datasets.values()
    )

    missing_after_text = sum(
        int(df.isna().sum().sum())
        for df in cleaned_datasets.values()
    )

    assert rows_after_text == (
        rows_before_text + len(translation_additions_df)
    )

    assert missing_after_text == missing_before_text

    assert unmatched_products == 0

    assert len(cleaned_datasets["products"]) == len(
        raw_datasets["products"]
    )


    # 12. Final summary

    print("\nCATEGORICAL STANDARDIZATION SUMMARY")

    print(
        "Text fields processed:",
        len(text_standardization_df)
    )

    print(
        "Fields with modified values:",
        text_standardization_df["records_changed"].gt(0).sum()
    )

    print(
        "Total text cells modified:",
        f"{text_standardization_df['records_changed'].sum():,}"
    )

    print("Original translation records:",
          translation_rows_before)

    print("Translation records added:",
          len(translation_additions_df))

    print("Final translation records:",
          translation_rows_after)

    print("Matched products:", f"{matched_products:,}")

    print("Unmatched products:", unmatched_products)

    print("Product category coverage:", f"{category_coverage_pct}%")

    print("Missing cells retained:", f"{missing_after_text:,}")

    print("Rows before:", f"{rows_before_text:,}")

    print("Rows after:", f"{rows_after_text:,}")

    print("Cleaning actions logged:", len(cleaning_log))

    print("\nStep 4.6 completed successfully.")

    # Transformation step 4.7
    # Step 4.7: Numerical anomaly and outlier treatment

    # 1. Reuse Phase 3 numerical profiling results

    source_numeric_profile_df = pd.read_excel(
        PROFILING_REPORT_PATH,
        sheet_name="Numerical Profiling",
        engine="openpyxl"
    )

    rows_before_numeric = sum(
        len(df) for df in cleaned_datasets.values()
    )

    missing_before_numeric = sum(
        int(df.isna().sum().sum())
        for df in cleaned_datasets.values()
    )

    fields_before_numeric = sum(
        len(df.columns)
        for df in cleaned_datasets.values()
    )

    numerical_treatment_records = []
    derived_numeric_fields = []


    # 2. Reusable quality flag function

    def add_numeric_flag(
        dataset_name,
        flag_column,
        condition,
        description,
        issue_id=None
    ):
        """Add a nullable Boolean quality indicator."""

        df = cleaned_datasets[dataset_name]

        assert flag_column not in df.columns

        flag = condition.astype("boolean")

        df[flag_column] = flag

        flagged_records = int(flag.sum())

        numerical_treatment_records.append({
            "dataset": dataset_name,
            "field": flag_column,
            "treatment": "Quality flag added",
            "affected_records": flagged_records,
            "unknown_flag_values": int(flag.isna().sum()),
            "issue_id": issue_id,
            "notes": description
        })

        derived_numeric_fields.append({
            "dataset": dataset_name,
            "column": flag_column,
            "description": description,
            "recommended_dtype": "BOOLEAN",
            "converted_dtype": "boolean",
            "primary_key_component": False,
            "relationship_targets": "None",
            "field_origin": "Derived"
        })

        log_cleaning_action(
            dataset=dataset_name,
            issue_id=issue_id,
            action=f"Created {flag_column}",
            affected_records=flagged_records,
            rows_before=len(df),
            rows_after=len(df),
            notes=description
        )


    # 3. Treat zero product weights

    products_df = cleaned_datasets["products"]

    zero_weight_mask = products_df["product_weight_g"].eq(0)

    add_numeric_flag(
        dataset_name="products",
        flag_column="is_zero_weight_source",
        condition=zero_weight_mask,
        description="Source product weight was recorded as zero.",
        issue_id="DQ008"
    )

    zero_weight_count = int(zero_weight_mask.sum())

    products_df["product_weight_g"] = (
        products_df["product_weight_g"]
        .mask(zero_weight_mask.fillna(False), pd.NA)
    )

    numerical_treatment_records.append({
        "dataset": "products",
        "field": "product_weight_g",
        "treatment": "Zero converted to missing",
        "affected_records": zero_weight_count,
        "unknown_flag_values": None,
        "issue_id": "DQ008",
        "notes": (
            "Exclude zero-weight observations from "
            "weight-dependent logistics calculations."
        )
    })

    log_cleaning_action(
        dataset="products",
        issue_id="DQ008",
        action="Converted zero product weights to missing",
        affected_records=zero_weight_count,
        rows_before=len(products_df),
        rows_after=len(products_df),
        notes="Original zero-weight observations remain flagged."
    )


    # 4. Preserve and flag zero freight values

    items_df = cleaned_datasets["order_items"]

    add_numeric_flag(
        dataset_name="order_items",
        flag_column="is_zero_freight",
        condition=items_df["freight_value"].eq(Decimal("0")),
        description="Recorded item freight value is zero.",
        issue_id="DQ024"
    )


    # 5. Preserve and flag payment anomalies

    payments_df = cleaned_datasets["payments"]

    add_numeric_flag(
        dataset_name="payments",
        flag_column="is_zero_installment",
        condition=payments_df["payment_installments"].eq(0),
        description="Payment installment count is recorded as zero.",
        issue_id="DQ026"
    )

    add_numeric_flag(
        dataset_name="payments",
        flag_column="is_zero_payment",
        condition=payments_df["payment_value"].eq(Decimal("0")),
        description="Recorded payment amount is zero.",
        issue_id="DQ027"
    )

    add_numeric_flag(
        dataset_name="payments",
        flag_column="is_undefined_payment_type",
        condition=payments_df["payment_type"].eq("not_defined"),
        description="Payment method is undefined in the source.",
        issue_id="DQ028"
    )


    # 6. Preserve and flag seller-declared revenue anomalies

    deals_df = cleaned_datasets["closed_deals"]

    add_numeric_flag(
        dataset_name="closed_deals",
        flag_column="is_zero_declared_revenue",
        condition=deals_df[
            "declared_monthly_revenue"
        ].eq(Decimal("0")),
        description=(
            "Declared monthly revenue is zero; "
            "its underlying meaning remains unverified."
        ),
        issue_id="DQ038"
    )

    # Project-defined screening threshold, not a verified limit

    DECLARED_REVENUE_REVIEW_THRESHOLD = Decimal("10000000")

    add_numeric_flag(
        dataset_name="closed_deals",
        flag_column="is_extreme_declared_revenue",
        condition=deals_df[
            "declared_monthly_revenue"
        ].gt(DECLARED_REVENUE_REVIEW_THRESHOLD),
        description=(
            "Declared monthly revenue exceeds the provisional "
            "review threshold of BRL 10 million."
        ),
        issue_id="DQ039"
    )


    # 7. Apply existing IQR thresholds
    # Reuse Phase 3 boundaries rather than recomputing them.

    iqr_source_df = source_numeric_profile_df.loc[
        source_numeric_profile_df["iqr_status"].eq("CALCULATED")
    ].copy()

    iqr_source_df = iqr_source_df.merge(
        column_mapping_df[
            ["dataset", "original_column", "standardized_column"]
        ],
        left_on=["dataset", "column"],
        right_on=["dataset", "original_column"],
        how="left",
        validate="one_to_one"
    )

    outlier_treatment_records = []

    for field in iqr_source_df.itertuples(index=False):

        dataset_name = field.dataset
        column = field.standardized_column

        series = cleaned_datasets[dataset_name][column]

        # Monetary fields remain Decimal in the actual datasets.
        if series.dtype == object:

            lower = Decimal(str(field.lower_fence))
            upper = Decimal(str(field.upper_fence))

        else:

            lower = float(field.lower_fence)
            upper = float(field.upper_fence)

        outlier_mask = (
            series.lt(lower) | series.gt(upper)
        ).astype("boolean")

        # Missing observations are not automatically non-outliers.
        outlier_mask = outlier_mask.mask(
            series.isna(), pd.NA
        )

        flag_column = f"is_{column}_outlier"

        add_numeric_flag(
            dataset_name=dataset_name,
            flag_column=flag_column,
            condition=outlier_mask,
            description=(
                f"Potential statistical outlier based on Phase 3 "
                f"IQR boundaries [{lower}, {upper}]."
            )
        )

        outlier_treatment_records.append({
            "dataset": dataset_name,
            "column": column,
            "lower_fence": float(lower),
            "upper_fence": float(upper),
            "phase3_outliers": int(field.potential_outliers),
            "current_outliers": int(outlier_mask.sum()),
            "missing_measurements": int(series.isna().sum()),
            "treatment": "Preserved and flagged"
        })


    # 8. Consolidate numerical treatment results

    numerical_treatment_df = pd.DataFrame(
        numerical_treatment_records
    )

    numeric_outlier_treatment_df = pd.DataFrame(
        outlier_treatment_records
    )

    print("COMMERCEIQ - NUMERICAL ANOMALY TREATMENT")

    display(
        numerical_treatment_df.loc[
            numerical_treatment_df["issue_id"].notna()
        ].reset_index(drop=True)
    )

    print("\nSTATISTICAL OUTLIER TREATMENT")

    display(numeric_outlier_treatment_df)


    # 9. Register newly derived fields in the working dictionary

    derived_numeric_dictionary_df = pd.DataFrame(
        derived_numeric_fields
    )

    # Mark existing source-derived fields
    if "field_origin" not in cleaning_dictionary_df.columns:

        cleaning_dictionary_df["field_origin"] = "Source"


    # Add current metadata for each derived indicator

    for index, field in derived_numeric_dictionary_df.iterrows():

        dataset_name = field["dataset"]
        column = field["column"]

        series = cleaned_datasets[dataset_name][column]

        derived_numeric_dictionary_df.loc[
            index, "total_records"
        ] = len(series)

        derived_numeric_dictionary_df.loc[
            index, "valid_records"
        ] = int(series.notna().sum())

        derived_numeric_dictionary_df.loc[
            index, "unique_values"
        ] = series.nunique()

        derived_numeric_dictionary_df.loc[
            index, "total_missing"
        ] = int(series.isna().sum())

        derived_numeric_dictionary_df.loc[
            index, "missing_pct"
        ] = round(series.isna().mean() * 100, 4)

        derived_numeric_dictionary_df.loc[
            index, "completeness_pct"
        ] = round(series.notna().mean() * 100, 4)

        derived_numeric_dictionary_df.loc[
            index, "current_dtype"
        ] = "boolean"

        derived_numeric_dictionary_df.loc[
            index, "cardinality"
        ] = (
            "Constant"
            if series.nunique() == 1
            else "Low"
        )


    cleaning_dictionary_df = pd.concat(
        [
            cleaning_dictionary_df,
            derived_numeric_dictionary_df
        ],
        ignore_index=True
    )


    # 10. Verify that financial values remain unchanged

    financial_fields = [
        ("order_items", "price"),
        ("order_items", "freight_value"),
        ("payments", "payment_value"),
        ("closed_deals", "declared_monthly_revenue")
    ]

    financial_preservation_records = []

    for dataset_name, column in financial_fields:

        original = raw_datasets[dataset_name][column].map(
            lambda value: Decimal(str(value))
        )

        current = cleaned_datasets[dataset_name][column]

        original_total = sum(original, Decimal("0"))
        current_total = sum(current, Decimal("0"))

        values_preserved = original.eq(current).all()

        financial_preservation_records.append({
            "dataset": dataset_name,
            "column": column,
            "original_total": original_total,
            "current_total": current_total,
            "difference": current_total - original_total,
            "status": (
                "PRESERVED"
                if values_preserved
                else "CHANGED"
            )
        })


    financial_preservation_df = pd.DataFrame(
        financial_preservation_records
    )

    print("\nFINANCIAL VALUE PRESERVATION")

    display(financial_preservation_df)


    # 11. Final reconciliation

    rows_after_numeric = sum(
        len(df) for df in cleaned_datasets.values()
    )

    missing_after_numeric = sum(
        int(df.isna().sum().sum())
        for df in cleaned_datasets.values()
    )

    fields_after_numeric = sum(
        len(df.columns)
        for df in cleaned_datasets.values()
    )

    new_flag_missing_values = int(
        derived_numeric_dictionary_df["total_missing"].sum()
    )

    assert rows_after_numeric == rows_before_numeric

    assert financial_preservation_df["status"].eq(
        "PRESERVED"
    ).all()

    assert products_df["product_weight_g"].eq(0).sum() == 0

    assert fields_after_numeric == (
        fields_before_numeric + len(derived_numeric_fields)
    )

    assert len(cleaning_dictionary_df) == fields_after_numeric

    assert missing_after_numeric == (
        missing_before_numeric
        + zero_weight_count
        + new_flag_missing_values
    )


    print("\nNUMERICAL TREATMENT SUMMARY")

    print("Zero product weights treated:", zero_weight_count)

    print(
        "Remaining missing product weights:",
        int(products_df["product_weight_g"].isna().sum())
    )

    print(
        "Zero freight records:",
        int(items_df["is_zero_freight"].sum())
    )

    print(
        "Zero payment installments:",
        int(payments_df["is_zero_installment"].sum())
    )

    print(
        "Zero payment records:",
        int(payments_df["is_zero_payment"].sum())
    )

    print(
        "Undefined payment records:",
        int(payments_df["is_undefined_payment_type"].sum())
    )

    print(
        "Zero declared revenue records:",
        int(deals_df["is_zero_declared_revenue"].sum())
    )

    print(
        "Extreme declared revenue records:",
        int(deals_df["is_extreme_declared_revenue"].sum())
    )

    print(
        "IQR fields processed:",
        len(numeric_outlier_treatment_df)
    )

    print(
        "Quality flags created:",
        len(derived_numeric_fields)
    )

    print(
        "Missing values introduced in source fields:",
        zero_weight_count
    )

    print(
        "Missing values in derived flags:",
        new_flag_missing_values
    )

    print("Total missing cells:", f"{missing_after_numeric:,}")

    print("Total fields:", fields_after_numeric)

    print("Total working rows:", f"{rows_after_numeric:,}")

    print("Rows removed:", rows_before_numeric - rows_after_numeric)

    print("Cleaning actions logged:", len(cleaning_log))

    print("\nStep 4.7 completed successfully.")

    # Transformation step 4.8
    # Step 4.8: Temporal inconsistency treatment

    # 1. Capture baseline

    rows_before_temporal = sum(
        len(df) for df in cleaned_datasets.values()
    )

    fields_before_temporal = sum(
        len(df.columns) for df in cleaned_datasets.values()
    )

    missing_before_temporal = sum(
        int(df.isna().sum().sum())
        for df in cleaned_datasets.values()
    )

    temporal_treatment_records = []
    derived_temporal_fields = []


    # 2. Define reusable temporal validation functions

    def compare_dates(earlier, later):
        """Flag reversed chronology; preserve unknown comparisons."""

        comparable = earlier.notna() & later.notna()

        return (
            later.lt(earlier)
            .astype("boolean")
            .mask(~comparable, pd.NA)
        )


    def valid_duration(earlier, later):
        """Determine whether a duration is eligible for calculation."""

        return (
            earlier.notna()
            & later.notna()
            & later.ge(earlier)
        ).astype("boolean")


    def add_temporal_flag(
        dataset_name,
        column,
        condition,
        description,
        issue_id=None,
        flag_type="Quality"
    ):
        """Create and document a temporal indicator."""

        df = cleaned_datasets[dataset_name]

        assert column not in df.columns

        flag = condition.astype("boolean")

        assert flag.index.equals(df.index)

        df[column] = flag

        true_count = int(flag.eq(True).sum())
        false_count = int(flag.eq(False).sum())
        missing_count = int(flag.isna().sum())

        temporal_treatment_records.append({
            "dataset": dataset_name,
            "column": column,
            "flag_type": flag_type,
            "true_count": true_count,
            "false_count": false_count,
            "unknown_count": missing_count,
            "issue_id": issue_id,
            "description": description
        })

        derived_temporal_fields.append({
            "dataset": dataset_name,
            "column": column,
            "description": description,
            "recommended_dtype": "BOOLEAN",
            "converted_dtype": "boolean",
            "current_dtype": "boolean",
            "primary_key_component": False,
            "relationship_targets": "None",
            "field_origin": "Derived",
            "total_records": len(df),
            "valid_records": int(flag.notna().sum()),
            "unique_values": flag.nunique(),
            "total_missing": missing_count,
            "missing_pct": round(flag.isna().mean() * 100, 4),
            "completeness_pct": round(
                flag.notna().mean() * 100, 4
            ),
            "cardinality": (
                "No valid values"
                if flag.nunique() == 0
                else "Constant"
                if flag.nunique() == 1
                else "Low"
            )
        })

        log_cleaning_action(
            dataset=dataset_name,
            issue_id=issue_id,
            action=f"Created {column}",
            affected_records=true_count,
            rows_before=len(df),
            rows_after=len(df),
            notes=description
        )


    # 3. Extract order lifecycle timestamps

    orders_df = cleaned_datasets["orders"]

    purchase = orders_df["order_purchase_timestamp"]
    approval = orders_df["order_approved_at"]
    carrier = orders_df["order_delivered_carrier_date"]
    delivery = orders_df["order_delivered_customer_date"]
    estimated = orders_df["order_estimated_delivery_date"]

    delivered_mask = orders_df["order_status"].eq("delivered")


    # 4. Flag missing timestamps in delivered orders

    missing_timestamp_rules = [
        (
            "is_delivered_missing_approval",
            delivered_mask & approval.isna(),
            "Delivered order without an approval timestamp.",
            "DQ014"
        ),
        (
            "is_delivered_missing_carrier",
            delivered_mask & carrier.isna(),
            "Delivered order without a carrier handover timestamp.",
            "DQ015"
        ),
        (
            "is_delivered_missing_delivery",
            delivered_mask & delivery.isna(),
            "Delivered order without a customer delivery timestamp.",
            "DQ016"
        )
    ]

    for column, condition, description, issue_id in (
        missing_timestamp_rules
    ):

        add_temporal_flag(
            "orders",
            column,
            condition,
            description,
            issue_id
        )


    # 5. Flag chronological inconsistencies

    chronology_rules = [
        (
            "is_carrier_before_purchase",
            purchase,
            carrier,
            "Carrier handover precedes order purchase.",
            "DQ017"
        ),
        (
            "is_carrier_before_approval",
            approval,
            carrier,
            "Carrier handover precedes order approval.",
            "DQ018"
        ),
        (
            "is_delivery_before_approval",
            approval,
            delivery,
            "Customer delivery precedes order approval.",
            "DQ019"
        ),
        (
            "is_delivery_before_carrier",
            carrier,
            delivery,
            "Customer delivery precedes carrier handover.",
            "DQ020"
        )
    ]

    for column, earlier, later, description, issue_id in (
        chronology_rules
    ):

        add_temporal_flag(
            "orders",
            column,
            compare_dates(earlier, later),
            description,
            issue_id
        )


    # 6. Create metric-specific eligibility indicators

    duration_eligibility_rules = [
        (
            "is_valid_approval_duration",
            valid_duration(purchase, approval),
            "Purchase and approval timestamps support a valid duration."
        ),
        (
            "is_valid_processing_duration",
            valid_duration(approval, carrier),
            "Approval and carrier timestamps support a valid duration."
        ),
        (
            "is_valid_transit_duration",
            valid_duration(carrier, delivery) & delivered_mask,
            "Delivered order supports a non-negative transit duration."
        ),
        (
            "is_valid_delivery_duration",
            valid_duration(purchase, delivery) & delivered_mask,
            "Delivered order supports a non-negative delivery duration."
        ),
        (
            "is_valid_estimated_delivery_duration",
            valid_duration(
                purchase.dt.normalize(),
                estimated.dt.normalize()
            ),
            "Purchase and estimated delivery dates support a valid duration."
        ),
        (
            "is_valid_delivery_promise_comparison",
            delivered_mask
            & valid_duration(purchase, delivery)
            & valid_duration(
                purchase.dt.normalize(),
                estimated.dt.normalize()
            ),
            "Delivered order supports actual-versus-estimated date comparison."
        )
    ]

    for column, condition, description in (
        duration_eligibility_rules
    ):

        add_temporal_flag(
            "orders",
            column,
            condition,
            description,
            flag_type="Eligibility"
        )


    # 7. Identify core reporting period

    CORE_REPORTING_START = pd.Timestamp("2017-01-01")
    CORE_REPORTING_END_EXCLUSIVE = pd.Timestamp("2018-09-01")

    core_period_mask = (
        purchase.ge(CORE_REPORTING_START)
        & purchase.lt(CORE_REPORTING_END_EXCLUSIVE)
    )

    add_temporal_flag(
        "orders",
        "is_core_reporting_period",
        core_period_mask,
        "Purchase falls within January 2017 to August 2018.",
        issue_id="DQ043",
        flag_type="Reporting scope"
    )


    # 8. Flag unusually distant shipping deadlines

    items_df = cleaned_datasets["order_items"]

    purchase_lookup = orders_df.set_index(
        "order_id"
    )["order_purchase_timestamp"]

    item_purchase_date = items_df["order_id"].map(
        purchase_lookup
    )

    shipping_deadline = items_df["shipping_limit_date"]

    shipping_deadline_days = (
        shipping_deadline - item_purchase_date
    ).dt.total_seconds() / 86400

    # Provisional screening threshold, not a contractual SLA
    SHIPPING_DEADLINE_REVIEW_DAYS = 180

    shipping_comparable = (
        item_purchase_date.notna()
        & shipping_deadline.notna()
    )

    distant_shipping_mask = (
        shipping_deadline_days
        .gt(SHIPPING_DEADLINE_REVIEW_DAYS)
        .astype("boolean")
        .mask(~shipping_comparable, pd.NA)
    )

    add_temporal_flag(
        "order_items",
        "is_distant_shipping_deadline",
        distant_shipping_mask,
        "Shipping deadline exceeds 180 days after order purchase.",
        issue_id="DQ025"
    )


    # 9. Validate marketing conversion chronology

    leads_df = cleaned_datasets["marketing_leads"]
    deals_df = cleaned_datasets["closed_deals"]

    lead_contact_lookup = leads_df.set_index(
        "mql_id"
    )["first_contact_date"]

    deal_contact = deals_df["mql_id"].map(
        lead_contact_lookup
    )

    won_date = deals_df["won_date"]

    add_temporal_flag(
        "closed_deals",
        "is_won_before_first_contact",
        compare_dates(deal_contact, won_date),
        "Deal won timestamp precedes recorded first contact.",
        issue_id="DQ032"
    )

    add_temporal_flag(
        "closed_deals",
        "is_valid_conversion_duration",
        valid_duration(deal_contact, won_date),
        "First contact and deal won dates support a non-negative duration.",
        flag_type="Eligibility"
    )


    # 10. Consolidate temporal treatment results

    temporal_treatment_df = pd.DataFrame(
        temporal_treatment_records
    )

    print("COMMERCEIQ - TEMPORAL QUALITY FLAGS")

    display(
        temporal_treatment_df.loc[
            temporal_treatment_df["flag_type"].eq("Quality"),
            [
                "dataset",
                "column",
                "true_count",
                "false_count",
                "unknown_count",
                "issue_id"
            ]
        ].reset_index(drop=True)
    )


    print("\nTEMPORAL METRIC ELIGIBILITY")

    display(
        temporal_treatment_df.loc[
            temporal_treatment_df["flag_type"].eq("Eligibility"),
            [
                "dataset",
                "column",
                "true_count",
                "false_count",
                "unknown_count"
            ]
        ].reset_index(drop=True)
    )


    # 11. Reporting period summary

    reporting_period_df = pd.DataFrame([
        {
            "reporting_scope": "Core reporting period",
            "order_count": int(core_period_mask.sum())
        },
        {
            "reporting_scope": "Outside core reporting period",
            "order_count": int((~core_period_mask).sum())
        }
    ])

    print("\nHISTORICAL REPORTING SCOPE")

    display(reporting_period_df)


    # 12. Register derived fields

    derived_temporal_dictionary_df = pd.DataFrame(
        derived_temporal_fields
    )

    cleaning_dictionary_df = pd.concat(
        [
            cleaning_dictionary_df,
            derived_temporal_dictionary_df
        ],
        ignore_index=True
    )


    # 13. Confirm source timestamps remain unchanged

    temporal_source_fields = source_dictionary_df.loc[
        source_dictionary_df["recommended_dtype"].isin(
            ["DATE", "DATETIME"]
        )
    ]

    timestamp_preservation_records = []

    for field in temporal_source_fields.itertuples(index=False):

        dataset_name = field.dataset
        column = field.column

        original = pd.to_datetime(
            raw_datasets[dataset_name][column],
            errors="raise",
            format="mixed"
        ).astype("datetime64[ns]")

        if field.recommended_dtype == "DATE":
            original = original.dt.normalize()

        current = cleaned_datasets[dataset_name][column]

        preserved = original.equals(current)

        timestamp_preservation_records.append({
            "dataset": dataset_name,
            "column": column,
            "status": (
                "PRESERVED" if preserved else "CHANGED"
            )
        })


    timestamp_preservation_df = pd.DataFrame(
        timestamp_preservation_records
    )

    print("\nSOURCE TIMESTAMP PRESERVATION")

    display(timestamp_preservation_df)


    # 14. Final reconciliation

    rows_after_temporal = sum(
        len(df) for df in cleaned_datasets.values()
    )

    fields_after_temporal = sum(
        len(df.columns) for df in cleaned_datasets.values()
    )

    missing_after_temporal = sum(
        int(df.isna().sum().sum())
        for df in cleaned_datasets.values()
    )

    temporal_flag_missing = int(
        derived_temporal_dictionary_df["total_missing"].sum()
    )

    assert rows_after_temporal == rows_before_temporal

    assert fields_after_temporal == (
        fields_before_temporal
        + len(derived_temporal_fields)
    )

    assert len(cleaning_dictionary_df) == fields_after_temporal

    assert missing_after_temporal == (
        missing_before_temporal
        + temporal_flag_missing
    )

    assert timestamp_preservation_df["status"].eq(
        "PRESERVED"
    ).all()

    assert reporting_period_df["order_count"].sum() == len(orders_df)


    print("\nTEMPORAL TREATMENT SUMMARY")

    print(
        "Temporal quality flags created:",
        temporal_treatment_df["flag_type"].eq("Quality").sum()
    )

    print(
        "Metric eligibility flags created:",
        temporal_treatment_df["flag_type"].eq("Eligibility").sum()
    )

    print(
        "Reporting scope flags created:",
        temporal_treatment_df["flag_type"].eq("Reporting scope").sum()
    )

    print(
        "Total temporal indicators created:",
        len(derived_temporal_fields)
    )

    print(
        "Source timestamp fields preserved:",
        timestamp_preservation_df["status"].eq("PRESERVED").sum()
    )

    print(
        "Orders in core reporting period:",
        f"{core_period_mask.sum():,}"
    )

    print(
        "Orders outside core reporting period:",
        f"{(~core_period_mask).sum():,}"
    )

    print(
        "Distant shipping deadlines:",
        int(distant_shipping_mask.sum())
    )

    print(
        "Missing values in temporal flags:",
        f"{temporal_flag_missing:,}"
    )

    print("Total missing cells:", f"{missing_after_temporal:,}")

    print("Total fields:", fields_after_temporal)

    print("Total working rows:", f"{rows_after_temporal:,}")

    print("Rows removed:", rows_before_temporal - rows_after_temporal)

    print("Cleaning actions logged:", len(cleaning_log))

    print("\nStep 4.8 completed successfully.")

    # Transformation step 4.9
    # Step 4.9: Geographic data cleaning and postal code lookup

    # 1. Capture geographic baseline

    geo_df = cleaned_datasets["geolocation"]

    geo_rows_before = len(geo_df)

    total_rows_before_geo = sum(
        len(df) for df in cleaned_datasets.values()
    )

    geographic_treatment_records = []
    derived_geographic_fields = []


    # 2. Define geographic validation rules

    # Approximate Brazil screening envelope, not an official border polygon
    BRAZIL_LAT_MIN = -34.0
    BRAZIL_LAT_MAX = 6.0

    BRAZIL_LNG_MIN = -74.0
    BRAZIL_LNG_MAX = -28.0

    BRAZIL_STATES = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF",
        "ES", "GO", "MA", "MT", "MS", "MG", "PA",
        "PB", "PR", "PE", "PI", "RJ", "RN", "RS",
        "RO", "RR", "SC", "SP", "SE", "TO"
    }


    # 3. Remove duplicates created by earlier standardization

    post_normalization_duplicates = int(
        geo_df.duplicated().sum()
    )

    geo_df = (
        geo_df.drop_duplicates()
        .reset_index(drop=True)
    )

    cleaned_datasets["geolocation"] = geo_df

    log_cleaning_action(
        dataset="geolocation",
        issue_id="DQ001",
        action="Removed post-normalization duplicates",
        affected_records=post_normalization_duplicates,
        rows_before=geo_rows_before,
        rows_after=len(geo_df),
        notes="Removed equivalent observations after text normalization."
    )


    # 4. Validate coordinate boundaries

    coordinates_available = (
        geo_df["geolocation_lat"].notna()
        & geo_df["geolocation_lng"].notna()
    )

    coordinate_validity = (
        geo_df["geolocation_lat"].between(
            BRAZIL_LAT_MIN, BRAZIL_LAT_MAX
        )
        & geo_df["geolocation_lng"].between(
            BRAZIL_LNG_MIN, BRAZIL_LNG_MAX
        )
    )

    geo_df["is_valid_brazil_coordinate"] = (
        coordinate_validity
        .astype("boolean")
        .mask(~coordinates_available, pd.NA)
    )


    # 5. Validate postal prefixes

    geo_df["is_valid_zip_prefix"] = (
        geo_df["geolocation_zip_code_prefix"]
        .str.fullmatch(r"[0-9]{5}")
        .astype("boolean")
    )


    # 6. Validate state abbreviations

    geo_df["is_valid_state"] = (
        geo_df["geolocation_state"]
        .isin(BRAZIL_STATES)
        .astype("boolean")
        .mask(
            geo_df["geolocation_state"].isna(),
            pd.NA
        )
    )


    # 7. Identify observations eligible for lookup construction

    geo_df["is_valid_geo_observation"] = (
        geo_df["is_valid_brazil_coordinate"].fillna(False)
        & geo_df["is_valid_zip_prefix"].fillna(False)
        & geo_df["is_valid_state"].fillna(False)
        & geo_df["geolocation_city"].notna()
        & geo_df["geolocation_city"].ne("").fillna(False)
    ).astype("boolean")


    # 8. Generate surrogate observation identifiers

    geo_df["geolocation_id"] = pd.Series(
        np.arange(1, len(geo_df) + 1),
        index=geo_df.index,
        dtype="Int64"
    )


    # 9. Summarize geographic quality checks

    geo_quality_rules = [
        (
            "is_valid_brazil_coordinate",
            "DQ003",
            "Coordinate within approximate Brazil screening envelope"
        ),
        (
            "is_valid_zip_prefix",
            None,
            "Postal prefix contains exactly five digits"
        ),
        (
            "is_valid_state",
            None,
            "State abbreviation belongs to a Brazilian federal unit"
        ),
        (
            "is_valid_geo_observation",
            None,
            "Observation eligible for geographic lookup construction"
        )
    ]

    for column, issue_id, description in geo_quality_rules:

        series = geo_df[column]

        valid_count = int(series.eq(True).sum())
        invalid_count = int(series.eq(False).sum())
        unknown_count = int(series.isna().sum())

        geographic_treatment_records.append({
            "validation_rule": column,
            "valid_records": valid_count,
            "invalid_records": invalid_count,
            "unknown_records": unknown_count,
            "description": description
        })

        log_cleaning_action(
            dataset="geolocation",
            issue_id=issue_id,
            action=f"Created {column}",
            affected_records=invalid_count,
            rows_before=len(geo_df),
            rows_after=len(geo_df),
            notes=description
        )

    log_cleaning_action(
        dataset="geolocation",
        action="Generated surrogate geographic observation identifiers",
        affected_records=len(geo_df),
        rows_before=len(geo_df),
        rows_after=len(geo_df)
    )


    geographic_validation_df = pd.DataFrame(
        geographic_treatment_records
    )

    print("COMMERCEIQ - GEOGRAPHIC VALIDATION")

    display(geographic_validation_df)


    # 10. Separate eligible and excluded observations

    eligible_geo_df = geo_df.loc[
        geo_df["is_valid_geo_observation"].eq(True)
    ].copy()

    excluded_geo_df = geo_df.loc[
        ~geo_df["is_valid_geo_observation"].fillna(False)
    ].copy()

    assert len(eligible_geo_df) + len(excluded_geo_df) == len(geo_df)


    # 11. Count city-state combinations per postal prefix

    geo_group_columns = [
        "geolocation_zip_code_prefix",
        "geolocation_city",
        "geolocation_state"
    ]

    geo_combination_counts_df = (
        eligible_geo_df
        .groupby(geo_group_columns, as_index=False)
        .size()
        .rename(columns={"size": "observation_count"})
    )


    # 12. Select the most frequently observed city-state combination
    # Alphabetical ordering provides a deterministic tie-break.

    dominant_geo_df = (
        geo_combination_counts_df
        .sort_values(
            [
                "geolocation_zip_code_prefix",
                "observation_count",
                "geolocation_state",
                "geolocation_city"
            ],
            ascending=[True, False, True, True]
        )
        .drop_duplicates(
            subset=["geolocation_zip_code_prefix"],
            keep="first"
        )
        .reset_index(drop=True)
    )


    # 13. Calculate representative coordinates within selected locations

    selected_geo_observations = eligible_geo_df.merge(
        dominant_geo_df[geo_group_columns],
        on=geo_group_columns,
        how="inner",
        validate="many_to_one"
    )

    representative_coordinates_df = (
        selected_geo_observations
        .groupby(
            geo_group_columns,
            as_index=False
        )
        .agg(
            latitude=("geolocation_lat", "median"),
            longitude=("geolocation_lng", "median"),
            selected_observation_count=(
                "geolocation_id", "count"
            )
        )
    )


    # 14. Calculate postal prefix ambiguity indicators

    postal_summary_df = (
        geo_combination_counts_df
        .groupby(
            "geolocation_zip_code_prefix",
            as_index=False
        )
        .agg(
            total_observations=("observation_count", "sum"),
            distinct_city_state_combinations=(
                "geolocation_city", "size"
            )
        )
    )


    # 15. Construct the unique geographic lookup

    geolocation_lookup_df = (
        representative_coordinates_df
        .merge(
            postal_summary_df,
            on="geolocation_zip_code_prefix",
            how="left",
            validate="one_to_one"
        )
        .rename(columns={
            "geolocation_zip_code_prefix": "zip_code_prefix",
            "geolocation_city": "city",
            "geolocation_state": "state"
        })
    )

    geolocation_lookup_df["is_ambiguous_zip"] = (
        geolocation_lookup_df[
            "distinct_city_state_combinations"
        ].gt(1).astype("boolean")
    )

    geolocation_lookup_df["dominant_location_pct"] = (
        geolocation_lookup_df["selected_observation_count"]
        / geolocation_lookup_df["total_observations"]
        * 100
    ).round(4).astype("Float64")

    geolocation_lookup_df = (
        geolocation_lookup_df
        .sort_values("zip_code_prefix")
        .reset_index(drop=True)
    )

    # Apply nullable analytical types

    for column in ["zip_code_prefix", "city", "state"]:

        geolocation_lookup_df[column] = (
            geolocation_lookup_df[column].astype("string")
        )

    for column in [
        "selected_observation_count",
        "total_observations",
        "distinct_city_state_combinations"
    ]:

        geolocation_lookup_df[column] = (
            geolocation_lookup_df[column].astype("Int64")
        )

    for column in ["latitude", "longitude"]:

        geolocation_lookup_df[column] = (
            geolocation_lookup_df[column].astype("Float64")
        )


    # Validate lookup grain

    assert geolocation_lookup_df["zip_code_prefix"].is_unique

    assert geolocation_lookup_df["zip_code_prefix"].notna().all()

    assert geolocation_lookup_df[
        ["latitude", "longitude"]
    ].notna().all().all()

    cleaned_datasets["geolocation_lookup"] = (
        geolocation_lookup_df
    )


    log_cleaning_action(
        dataset="geolocation_lookup",
        issue_id="DQ002",
        action="Constructed unique postal prefix lookup",
        affected_records=len(geolocation_lookup_df),
        rows_before=0,
        rows_after=len(geolocation_lookup_df),
        notes=(
            "Derived lookup using dominant city-state combinations "
            "and median coordinates."
        )
    )


    # 16. Validate customer and seller geographic coverage

    geographic_coverage_records = []

    for dataset_name, column in [
        ("customers", "customer_zip_code_prefix"),
        ("sellers", "seller_zip_code_prefix")
    ]:

        df = cleaned_datasets[dataset_name]

        matched_mask = df[column].isin(
            geolocation_lookup_df["zip_code_prefix"]
        )

        matched_count = int(matched_mask.sum())
        unmatched_count = int((~matched_mask).sum())

        geographic_coverage_records.append({
            "dataset": dataset_name,
            "total_records": len(df),
            "matched_records": matched_count,
            "unmatched_records": unmatched_count,
            "coverage_pct": round(
                matched_count / len(df) * 100, 4
            )
        })


    geographic_coverage_df = pd.DataFrame(
        geographic_coverage_records
    )

    print("\nCUSTOMER AND SELLER GEOGRAPHIC COVERAGE")

    display(geographic_coverage_df)


    # 17. Register geographic metadata

    geo_field_definitions = {
        "geolocation_id": (
            "Generated geographic observation identifier",
            "INTEGER"
        ),

        "is_valid_brazil_coordinate": (
            "Coordinate within approximate Brazil screening envelope",
            "BOOLEAN"
        ),

        "is_valid_zip_prefix": (
            "Postal prefix contains exactly five digits",
            "BOOLEAN"
        ),

        "is_valid_state": (
            "Valid Brazilian federal unit abbreviation",
            "BOOLEAN"
        ),

        "is_valid_geo_observation": (
            "Observation eligible for geographic lookup calculations",
            "BOOLEAN"
        )
    }


    lookup_field_definitions = {
        "zip_code_prefix": (
            "Unique five-digit postal prefix",
            "STRING"
        ),

        "city": (
            "Most frequently observed city in selected city-state combination",
            "STRING"
        ),

        "state": (
            "State associated with selected city-state combination",
            "STRING"
        ),

        "latitude": (
            "Median latitude of selected geographic observations",
            "FLOAT"
        ),

        "longitude": (
            "Median longitude of selected geographic observations",
            "FLOAT"
        ),

        "selected_observation_count": (
            "Observations supporting selected city-state combination",
            "INTEGER"
        ),

        "total_observations": (
            "Total eligible observations for postal prefix",
            "INTEGER"
        ),

        "distinct_city_state_combinations": (
            "Number of observed city-state combinations",
            "INTEGER"
        ),

        "is_ambiguous_zip": (
            "Postal prefix has multiple city-state combinations",
            "BOOLEAN"
        ),

        "dominant_location_pct": (
            "Percentage of observations supporting selected location",
            "FLOAT"
        )
    }


    for dataset_name, field_definitions, grain, primary_key in [
        (
            "geolocation",
            geo_field_definitions,
            "One cleaned geographic observation",
            "geolocation_id"
        ),
        (
            "geolocation_lookup",
            lookup_field_definitions,
            "One record per eligible postal prefix",
            "zip_code_prefix"
        )
    ]:

        df = cleaned_datasets[dataset_name]

        for column, (description, target_dtype) in (
            field_definitions.items()
        ):

            series = df[column]

            unique_count = series.nunique()
            valid_count = int(series.notna().sum())

            if unique_count == 0:
                cardinality = "No valid values"
            elif unique_count == 1:
                cardinality = "Constant"
            elif unique_count == valid_count:
                cardinality = "Unique"
            elif unique_count <= 20:
                cardinality = "Low"
            elif unique_count <= 100:
                cardinality = "Medium"
            else:
                cardinality = "High"

            derived_geographic_fields.append({
                "dataset": dataset_name,
                "column": column,
                "description": description,
                "grain": grain,
                "recommended_dtype": target_dtype,
                "converted_dtype": str(series.dtype),
                "current_dtype": str(series.dtype),
                "primary_key_component": column == primary_key,
                "relationship_targets": "None",
                "field_origin": "Derived",
                "total_records": len(series),
                "valid_records": valid_count,
                "unique_values": unique_count,
                "cardinality": cardinality,
                "total_missing": int(series.isna().sum()),
                "missing_pct": round(series.isna().mean() * 100, 4),
                "completeness_pct": round(
                    series.notna().mean() * 100, 4
                )
            })


    derived_geographic_dictionary_df = pd.DataFrame(
        derived_geographic_fields
    )

    cleaning_dictionary_df = pd.concat(
        [
            cleaning_dictionary_df,
            derived_geographic_dictionary_df
        ],
        ignore_index=True
    )


    # 18. Validate final geographic structure

    assert geo_df["geolocation_id"].is_unique

    assert geo_df["geolocation_id"].notna().all()

    assert len(cleaning_dictionary_df) == sum(
        len(df.columns) for df in cleaned_datasets.values()
    )

    assert len(cleaned_datasets["customers"]) == len(
        raw_datasets["customers"]
    )

    assert len(cleaned_datasets["sellers"]) == len(
        raw_datasets["sellers"]
    )


    # 19. Final geographic summary

    geographic_summary_df = pd.DataFrame([
        {
            "metric": "Geolocation records before step",
            "value": geo_rows_before
        },
        {
            "metric": "Post-normalization duplicates removed",
            "value": post_normalization_duplicates
        },
        {
            "metric": "Remaining geographic observations",
            "value": len(geo_df)
        },
        {
            "metric": "Eligible geographic observations",
            "value": len(eligible_geo_df)
        },
        {
            "metric": "Observations excluded from lookup",
            "value": len(excluded_geo_df)
        },
        {
            "metric": "Unique postal prefixes in lookup",
            "value": len(geolocation_lookup_df)
        },
        {
            "metric": "Ambiguous postal prefixes",
            "value": int(
                geolocation_lookup_df["is_ambiguous_zip"].sum()
            )
        }
    ])

    print("\nGEOGRAPHIC CLEANING SUMMARY")

    display(geographic_summary_df)


    total_rows_after_geo = sum(
        len(df) for df in cleaned_datasets.values()
    )

    assert total_rows_after_geo == (
        total_rows_before_geo
        - post_normalization_duplicates
        + len(geolocation_lookup_df)
    )

    print("\nFINAL GEOGRAPHIC TRANSFORMATION SUMMARY")

    print("Working datasets:", len(cleaned_datasets))

    print(
        "Post-normalization duplicates removed:",
        f"{post_normalization_duplicates:,}"
    )

    print("Geolocation observations:", f"{len(geo_df):,}")

    print(
        "Excluded geographic observations:",
        f"{len(excluded_geo_df):,}"
    )

    print(
        "Unique postal lookup records:",
        f"{len(geolocation_lookup_df):,}"
    )

    print(
        "Duplicate postal lookup keys:",
        geolocation_lookup_df["zip_code_prefix"].duplicated().sum()
    )

    print(
        "Ambiguous postal prefixes:",
        int(geolocation_lookup_df["is_ambiguous_zip"].sum())
    )

    print(
        "New geographic fields:",
        len(derived_geographic_fields)
    )

    print(
        "Total fields:",
        sum(len(df.columns) for df in cleaned_datasets.values())
    )

    print("Total working rows:", f"{total_rows_after_geo:,}")

    print("Cleaning actions logged:", len(cleaning_log))

    print("\nStep 4.9 completed successfully.")

    # Transformation step 4.10
    # Step 4.10: Relationship and referential integrity management

    # 1. Capture baseline

    rows_before_relationships = sum(
        len(df) for df in cleaned_datasets.values()
    )

    fields_before_relationships = sum(
        len(df.columns) for df in cleaned_datasets.values()
    )

    missing_before_relationships = sum(
        int(df.isna().sum().sum())
        for df in cleaned_datasets.values()
    )

    source_relationship_df = pd.read_excel(
        PROFILING_REPORT_PATH,
        sheet_name="Relationships",
        engine="openpyxl"
    )


    # 2. Define cleaned dataset relationships
    # Required relationships must have complete referential integrity.
    # Optional relationships may legitimately contain unmatched records.

    cleaned_relationships = [
        ("orders", "customer_id",
         "customers", "customer_id", "Required"),

        ("order_items", "order_id",
         "orders", "order_id", "Required"),

        ("order_items", "product_id",
         "products", "product_id", "Required"),

        ("order_items", "seller_id",
         "sellers", "seller_id", "Required"),

        ("payments", "order_id",
         "orders", "order_id", "Required"),

        ("reviews", "order_id",
         "orders", "order_id", "Required"),

        ("products", "product_category_name",
         "category_translation", "product_category_name",
         "Required"),

        ("customers", "customer_zip_code_prefix",
         "geolocation_lookup", "zip_code_prefix",
         "Optional"),

        ("sellers", "seller_zip_code_prefix",
         "geolocation_lookup", "zip_code_prefix",
         "Optional"),

        ("closed_deals", "mql_id",
         "marketing_leads", "mql_id", "Required"),

        ("closed_deals", "seller_id",
         "sellers", "seller_id", "Optional")
    ]


    # 3. Validate cleaned relationships

    relationship_validation_records = []
    unmatched_relationship_records = []

    for (
        child_name,
        child_key,
        parent_name,
        parent_key,
        relationship_type
    ) in cleaned_relationships:

        child = cleaned_datasets[child_name][child_key]
        parent = cleaned_datasets[parent_name][parent_key]

        # Parent keys must support safe relational joins
        assert parent.is_unique
        assert parent.notna().all()

        child_valid = child.dropna()

        matched_mask = child_valid.isin(parent)

        matched_rows = int(matched_mask.sum())

        unmatched_rows = int((~matched_mask).sum())

        missing_child_keys = int(child.isna().sum())

        child_keys = set(child_valid.unique())
        parent_keys = set(parent.unique())

        unmatched_keys = child_keys - parent_keys

        unused_parent_keys = parent_keys - child_keys

        cardinality = (
            "One-to-one"
            if child_valid.is_unique
            else "Many-to-one"
        )

        if unmatched_rows == 0 and missing_child_keys == 0:

            status = "COMPLETE MATCH"

        elif relationship_type == "Optional":

            status = "EXPECTED COVERAGE GAP"

        else:

            status = "INTEGRITY FAILURE"

        relationship_validation_records.append({
            "child_dataset": child_name,
            "child_key": child_key,
            "parent_dataset": parent_name,
            "parent_key": parent_key,
            "relationship_type": relationship_type,
            "cardinality": cardinality,
            "child_rows": len(child),
            "missing_child_keys": missing_child_keys,
            "matched_rows": matched_rows,
            "unmatched_rows": unmatched_rows,
            "unmatched_distinct_keys": len(unmatched_keys),
            "unused_parent_keys": len(unused_parent_keys),
            "coverage_pct": round(
                matched_rows / len(child) * 100, 4
            ) if len(child) else None,
            "status": status
        })

        for key in sorted(unmatched_keys):

            unmatched_relationship_records.append({
                "child_dataset": child_name,
                "child_key": child_key,
                "parent_dataset": parent_name,
                "unmatched_key": key,
                "relationship_type": relationship_type
            })


    cleaned_relationship_df = pd.DataFrame(
        relationship_validation_records
    )

    unmatched_relationship_df = pd.DataFrame(
        unmatched_relationship_records,
        columns=[
            "child_dataset",
            "child_key",
            "parent_dataset",
            "unmatched_key",
            "relationship_type"
        ]
    )

    print("COMMERCEIQ - CLEANED RELATIONSHIP VALIDATION")

    display(cleaned_relationship_df)

    assert not cleaned_relationship_df["status"].eq(
        "INTEGRITY FAILURE"
    ).any()


    # 4. Compare Phase 3 and Phase 4 relationship coverage

    relationship_comparison_records = []

    for row in cleaned_relationship_df.itertuples(index=False):

        original_parent = (
            "geolocation"
            if row.parent_dataset == "geolocation_lookup"
            else row.parent_dataset
        )

        original = source_relationship_df.loc[
            source_relationship_df["child_dataset"].eq(
                row.child_dataset
            )
            & source_relationship_df["child_key"].eq(
                row.child_key
            )
            & source_relationship_df["parent_dataset"].eq(
                original_parent
            )
        ].iloc[0]

        # Use all child records as denominator for both phases
        original_coverage = (
            original["matched_rows"]
            / original["child_rows"]
            * 100
        )

        relationship_comparison_records.append({
            "child_dataset": row.child_dataset,
            "parent_dataset": row.parent_dataset,
            "phase3_cardinality": original["cardinality"],
            "phase4_cardinality": row.cardinality,
            "phase3_missing_or_unmatched": int(
                original["missing_child_keys"]
                + original["unmatched_rows"]
            ),
            "phase4_missing_or_unmatched": (
                row.missing_child_keys
                + row.unmatched_rows
            ),
            "phase3_coverage_pct": round(
                original_coverage, 4
            ),
            "phase4_coverage_pct": row.coverage_pct,
            "status": row.status
        })


    relationship_comparison_df = pd.DataFrame(
        relationship_comparison_records
    )

    print("\nPHASE 3 VS PHASE 4 RELATIONSHIP COMPARISON")

    display(relationship_comparison_df)


    # 5. Create relationship coverage indicators

    relationship_flag_records = []
    derived_relationship_fields = []


    def add_relationship_flag(
        dataset_name,
        column,
        condition,
        description,
        issue_id=None
    ):

        df = cleaned_datasets[dataset_name]

        assert column not in df.columns
        assert condition.index.equals(df.index)

        flag = condition.astype("boolean")

        df[column] = flag

        true_count = int(flag.eq(True).sum())
        false_count = int(flag.eq(False).sum())
        missing_count = int(flag.isna().sum())

        relationship_flag_records.append({
            "dataset": dataset_name,
            "column": column,
            "true_count": true_count,
            "false_count": false_count,
            "unknown_count": missing_count,
            "issue_id": issue_id,
            "description": description
        })

        derived_relationship_fields.append({
            "dataset": dataset_name,
            "column": column,
            "description": description,
            "recommended_dtype": "BOOLEAN",
            "converted_dtype": "boolean",
            "current_dtype": "boolean",
            "primary_key_component": False,
            "relationship_targets": "None",
            "field_origin": "Derived",
            "total_records": len(df),
            "valid_records": int(flag.notna().sum()),
            "unique_values": flag.nunique(),
            "cardinality": (
                "Constant" if flag.nunique() == 1 else "Low"
            ),
            "total_missing": missing_count,
            "missing_pct": round(flag.isna().mean() * 100, 4),
            "completeness_pct": round(
                flag.notna().mean() * 100, 4
            )
        })

        log_cleaning_action(
            dataset=dataset_name,
            issue_id=issue_id,
            action=f"Created {column}",
            affected_records=true_count,
            rows_before=len(df),
            rows_after=len(df),
            notes=description
        )


    # 6. Order relationship indicators

    orders_df = cleaned_datasets["orders"]

    for source_dataset, flag_column, description, issue_id in [
        (
            "order_items",
            "has_order_items",
            "Order has at least one recorded item.",
            "DQ021"
        ),
        (
            "payments",
            "has_payment_records",
            "Order has at least one recorded payment.",
            "DQ022"
        ),
        (
            "reviews",
            "has_review_records",
            "Order has at least one recorded review.",
            "DQ023"
        )
    ]:

        add_relationship_flag(
            "orders",
            flag_column,
            orders_df["order_id"].isin(
                cleaned_datasets[source_dataset]["order_id"]
            ),
            description,
            issue_id
        )


    # 7. Geographic coverage indicators

    geo_lookup = cleaned_datasets["geolocation_lookup"]

    for dataset_name, key, issue_id in [
        ("customers", "customer_zip_code_prefix", "DQ029"),
        ("sellers", "seller_zip_code_prefix", "DQ030")
    ]:

        df = cleaned_datasets[dataset_name]

        add_relationship_flag(
            dataset_name,
            "has_geolocation_match",
            df[key].isin(geo_lookup["zip_code_prefix"]),
            "Postal prefix matches the cleaned geographic lookup.",
            issue_id
        )


    # 8. Marketing funnel relationship indicators

    leads_df = cleaned_datasets["marketing_leads"]
    deals_df = cleaned_datasets["closed_deals"]
    sellers_df = cleaned_datasets["sellers"]

    add_relationship_flag(
        "marketing_leads",
        "has_closed_deal",
        leads_df["mql_id"].isin(deals_df["mql_id"]),
        "Marketing lead has a recorded closed deal."
    )

    add_relationship_flag(
        "closed_deals",
        "has_marketplace_seller_match",
        deals_df["seller_id"].isin(sellers_df["seller_id"]),
        "Closed-deal seller appears in the marketplace dataset.",
        "DQ033"
    )

    add_relationship_flag(
        "sellers",
        "has_recorded_marketing_deal",
        sellers_df["seller_id"].isin(deals_df["seller_id"]),
        "Marketplace seller appears in the recorded marketing deals."
    )


    # 9. Consolidate relationship coverage flags

    relationship_flags_df = pd.DataFrame(
        relationship_flag_records
    )

    print("\nRELATIONSHIP COVERAGE INDICATORS")

    display(
        relationship_flags_df[
            [
                "dataset",
                "column",
                "true_count",
                "false_count",
                "unknown_count",
                "issue_id"
            ]
        ]
    )


    # 10. Test safe geographic joins
    # Use temporary joins without permanently merging datasets.

    join_validation_records = []

    for dataset_name, join_key in [
        ("customers", "customer_zip_code_prefix"),
        ("sellers", "seller_zip_code_prefix")
    ]:

        df = cleaned_datasets[dataset_name]

        joined = df[[join_key]].merge(
            geo_lookup[["zip_code_prefix"]],
            left_on=join_key,
            right_on="zip_code_prefix",
            how="left",
            validate="many_to_one",
            indicator=True
        )

        join_validation_records.append({
            "dataset": dataset_name,
            "join_target": "geolocation_lookup",
            "rows_before_join": len(df),
            "rows_after_join": len(joined),
            "matched_rows": int(joined["_merge"].eq("both").sum()),
            "unmatched_rows": int(
                joined["_merge"].eq("left_only").sum()
            ),
            "row_multiplication": len(joined) - len(df),
            "status": "PASS" if len(joined) == len(df) else "FAIL"
        })

        assert len(joined) == len(df)


    join_validation_df = pd.DataFrame(
        join_validation_records
    )

    print("\nGEOGRAPHIC JOIN SAFETY VALIDATION")

    display(join_validation_df)


    # 11. Analyze missing transaction relationships by order status

    order_relationship_coverage_df = (
        orders_df.assign(
            missing_items=~orders_df["has_order_items"],
            missing_payments=~orders_df["has_payment_records"],
            missing_reviews=~orders_df["has_review_records"]
        )
        .groupby("order_status", as_index=False)
        .agg(
            total_orders=("order_id", "size"),
            orders_without_items=("missing_items", "sum"),
            orders_without_payments=("missing_payments", "sum"),
            orders_without_reviews=("missing_reviews", "sum")
        )
        .sort_values("total_orders", ascending=False)
    )

    print("\nORDER RELATIONSHIP COVERAGE BY STATUS")

    display(order_relationship_coverage_df)


    # 12. Update working data dictionary

    derived_relationship_dictionary_df = pd.DataFrame(
        derived_relationship_fields
    )

    cleaning_dictionary_df = pd.concat(
        [
            cleaning_dictionary_df,
            derived_relationship_dictionary_df
        ],
        ignore_index=True
    )

    # Update geographic relationship targets
    for dataset_name, column in [
        ("customers", "customer_zip_code_prefix"),
        ("sellers", "seller_zip_code_prefix")
    ]:

        dictionary_mask = (
            cleaning_dictionary_df["dataset"].eq(dataset_name)
            & cleaning_dictionary_df["column"].eq(column)
        )

        cleaning_dictionary_df.loc[
            dictionary_mask,
            "relationship_targets"
        ] = "geolocation_lookup.zip_code_prefix"


    # 13. Final reconciliation

    rows_after_relationships = sum(
        len(df) for df in cleaned_datasets.values()
    )

    fields_after_relationships = sum(
        len(df.columns) for df in cleaned_datasets.values()
    )

    missing_after_relationships = sum(
        int(df.isna().sum().sum())
        for df in cleaned_datasets.values()
    )

    required_relationships = cleaned_relationship_df.loc[
        cleaned_relationship_df["relationship_type"].eq("Required")
    ]

    optional_relationships = cleaned_relationship_df.loc[
        cleaned_relationship_df["relationship_type"].eq("Optional")
    ]

    assert required_relationships["status"].eq(
        "COMPLETE MATCH"
    ).all()

    assert rows_after_relationships == rows_before_relationships

    assert fields_after_relationships == (
        fields_before_relationships
        + len(derived_relationship_fields)
    )

    assert len(cleaning_dictionary_df) == fields_after_relationships

    assert missing_after_relationships == missing_before_relationships

    assert join_validation_df["status"].eq("PASS").all()

    assert relationship_flags_df["unknown_count"].eq(0).all()


    print("\nRELATIONSHIP MANAGEMENT SUMMARY")

    print(
        "Relationships validated:",
        len(cleaned_relationship_df)
    )

    print(
        "Required relationships:",
        len(required_relationships)
    )

    print(
        "Required relationships passed:",
        required_relationships["status"].eq(
            "COMPLETE MATCH"
        ).sum()
    )

    print(
        "Optional relationships:",
        len(optional_relationships)
    )

    print(
        "Expected coverage gaps:",
        cleaned_relationship_df["status"].eq(
            "EXPECTED COVERAGE GAP"
        ).sum()
    )

    print(
        "Integrity failures:",
        cleaned_relationship_df["status"].eq(
            "INTEGRITY FAILURE"
        ).sum()
    )

    print(
        "Many-to-many relationships remaining:",
        cleaned_relationship_df["cardinality"].eq(
            "Many-to-many"
        ).sum()
    )

    print(
        "Relationship flags created:",
        len(derived_relationship_fields)
    )

    print(
        "Geographic join tests passed:",
        join_validation_df["status"].eq("PASS").sum()
    )

    print("Total fields:", fields_after_relationships)

    print("Total working rows:", f"{rows_after_relationships:,}")

    print("Rows removed:",
          rows_before_relationships - rows_after_relationships)

    print("Cleaning actions logged:", len(cleaning_log))

    print("\nStep 4.10 completed successfully.")

    # Transformation step 4.11
    # Step 4.11: Business-oriented feature engineering

    # 1. Capture baseline

    rows_before_features = sum(
        len(df) for df in cleaned_datasets.values()
    )

    fields_before_features = sum(
        len(df.columns) for df in cleaned_datasets.values()
    )

    feature_records = []
    derived_business_fields = []


    # 2. Reusable feature registration function

    def add_business_feature(
        dataset_name,
        column,
        values,
        analytical_type,
        description
    ):
        """Create and document a business-oriented derived feature."""

        df = cleaned_datasets[dataset_name]

        assert column not in df.columns
        assert values.index.equals(df.index)

        dtype_mapping = {
            "STRING": "string",
            "INTEGER": "Int64",
            "FLOAT": "Float64",
            "BOOLEAN": "boolean",
            "DECIMAL": "object",
            "DATE": "datetime64[ns]"
        }

        values = values.astype(
            dtype_mapping[analytical_type]
        )

        df[column] = values

        valid_count = int(values.notna().sum())
        missing_count = int(values.isna().sum())
        unique_count = values.nunique()

        if unique_count == 0:
            cardinality = "No valid values"

        elif unique_count == 1:
            cardinality = "Constant"

        elif unique_count == valid_count:
            cardinality = "Unique"

        elif unique_count <= 20:
            cardinality = "Low"

        elif unique_count <= 100:
            cardinality = "Medium"

        else:
            cardinality = "High"

        feature_records.append({
            "dataset": dataset_name,
            "feature": column,
            "analytical_type": analytical_type,
            "actual_dtype": str(values.dtype),
            "valid_records": valid_count,
            "missing_records": missing_count,
            "description": description
        })

        derived_business_fields.append({
            "dataset": dataset_name,
            "column": column,
            "description": description,
            "recommended_dtype": analytical_type,
            "converted_dtype": str(values.dtype),
            "current_dtype": str(values.dtype),
            "primary_key_component": False,
            "relationship_targets": "None",
            "field_origin": "Derived",
            "total_records": len(df),
            "valid_records": valid_count,
            "unique_values": unique_count,
            "cardinality": cardinality,
            "total_missing": missing_count,
            "missing_pct": round(
                values.isna().mean() * 100, 4
            ),
            "completeness_pct": round(
                values.notna().mean() * 100, 4
            )
        })

        log_cleaning_action(
            dataset=dataset_name,
            action=f"Created business feature: {column}",
            affected_records=valid_count,
            rows_before=len(df),
            rows_after=len(df),
            notes=description
        )


    # 3. Reusable duration calculation function

    def calculate_duration(
        earlier,
        later,
        eligibility,
        unit="days"
    ):
        """Calculate duration only for eligible observations."""

        seconds = (later - earlier).dt.total_seconds()

        divisors = {
            "hours": 3600,
            "days": 86400
        }

        duration = seconds / divisors[unit]

        return (
            duration
            .where(eligibility.fillna(False))
            .round(4)
            .astype("Float64")
        )


    # ============================================================
    # 4. ORDER FEATURES
    # ============================================================

    orders_df = cleaned_datasets["orders"]

    purchase = orders_df["order_purchase_timestamp"]
    approval = orders_df["order_approved_at"]
    carrier = orders_df["order_delivered_carrier_date"]
    delivery = orders_df["order_delivered_customer_date"]
    estimated = orders_df["order_estimated_delivery_date"]


    # 4.1 Calendar features

    calendar_features = [
        (
            "purchase_date",
            purchase.dt.normalize(),
            "DATE",
            "Calendar date of order purchase."
        ),
        (
            "purchase_year",
            purchase.dt.year,
            "INTEGER",
            "Calendar year of order purchase."
        ),
        (
            "purchase_month",
            purchase.dt.month,
            "INTEGER",
            "Calendar month number of order purchase."
        ),
        (
            "purchase_year_month",
            purchase.dt.strftime("%Y-%m"),
            "STRING",
            "Year-month reporting period of order purchase."
        ),
        (
            "purchase_quarter",
            purchase.dt.quarter,
            "INTEGER",
            "Calendar quarter of order purchase."
        ),
        (
            "purchase_day_of_week",
            purchase.dt.day_of_week + 1,
            "INTEGER",
            "Purchase weekday; Monday=1 and Sunday=7."
        ),
        (
            "purchase_hour",
            purchase.dt.hour,
            "INTEGER",
            "Hour of order purchase in source-local time."
        )
    ]

    for column, values, dtype, description in calendar_features:

        add_business_feature(
            "orders",
            column,
            values,
            dtype,
            description
        )


    # 4.2 Operational duration features

    order_duration_features = [
        (
            "approval_duration_hours",
            purchase,
            approval,
            "is_valid_approval_duration",
            "hours",
            "Elapsed hours from order purchase to approval."
        ),
        (
            "processing_duration_days",
            approval,
            carrier,
            "is_valid_processing_duration",
            "days",
            "Elapsed days from approval to carrier handover."
        ),
        (
            "transit_duration_days",
            carrier,
            delivery,
            "is_valid_transit_duration",
            "days",
            "Elapsed days from carrier handover to customer delivery."
        ),
        (
            "delivery_duration_days",
            purchase,
            delivery,
            "is_valid_delivery_duration",
            "days",
            "Elapsed days from purchase to customer delivery."
        ),
        (
            "estimated_delivery_days",
            purchase.dt.normalize(),
            estimated.dt.normalize(),
            "is_valid_estimated_delivery_duration",
            "days",
            "Estimated delivery lead time in calendar days."
        )
    ]

    for (
        column,
        earlier,
        later,
        eligibility_column,
        unit,
        description
    ) in order_duration_features:

        duration = calculate_duration(
            earlier,
            later,
            orders_df[eligibility_column],
            unit
        )

        add_business_feature(
            "orders",
            column,
            duration,
            "FLOAT",
            description
        )


    # 4.3 Delivery performance

    delivery_eligible = orders_df[
        "is_valid_delivery_promise_comparison"
    ]

    delivery_deviation = (
        delivery.dt.normalize()
        - estimated.dt.normalize()
    ).dt.days.where(delivery_eligible)

    add_business_feature(
        "orders",
        "delivery_deviation_days",
        delivery_deviation,
        "INTEGER",
        "Actual delivery date minus estimated delivery date."
    )


    on_time_delivery = (
        delivery_deviation.le(0)
        .astype("boolean")
        .mask(~delivery_eligible, pd.NA)
    )

    add_business_feature(
        "orders",
        "is_on_time_delivery",
        on_time_delivery,
        "BOOLEAN",
        "Delivered on or before the estimated delivery date."
    )


    delivery_performance = pd.Series(
        pd.NA,
        index=orders_df.index,
        dtype="string"
    )

    delivery_performance.loc[
        delivery_eligible
        & delivery_deviation.lt(0)
    ] = "early"

    delivery_performance.loc[
        delivery_eligible
        & delivery_deviation.eq(0)
    ] = "on_time"

    delivery_performance.loc[
        delivery_eligible
        & delivery_deviation.gt(0)
    ] = "late"

    add_business_feature(
        "orders",
        "delivery_performance",
        delivery_performance,
        "STRING",
        "Delivery performance classification: early, on_time or late."
    )


    # ============================================================
    # 5. ORDER ITEM FEATURES
    # ============================================================

    items_df = cleaned_datasets["order_items"]

    price = items_df["price"]
    freight = items_df["freight_value"]

    item_total = price + freight

    add_business_feature(
        "order_items",
        "item_value_with_freight",
        item_total,
        "DECIMAL",
        "Recorded merchandise price plus item freight value in BRL."
    )


    def safe_percentage(numerator, denominator):
        """Calculate percentage without dividing by zero."""

        result = []

        for n, d in zip(numerator, denominator):

            if pd.isna(n) or pd.isna(d) or d <= 0:
                result.append(pd.NA)

            else:
                result.append(
                    round(float(n / d * 100), 4)
                )

        return pd.Series(
            result,
            index=numerator.index,
            dtype="Float64"
        )


    add_business_feature(
        "order_items",
        "freight_to_price_pct",
        safe_percentage(freight, price),
        "FLOAT",
        "Freight value as a percentage of merchandise price."
    )

    add_business_feature(
        "order_items",
        "freight_share_of_item_total_pct",
        safe_percentage(freight, item_total),
        "FLOAT",
        "Freight value as a percentage of merchandise plus freight."
    )


    # ============================================================
    # 6. PRODUCT FEATURES
    # ============================================================

    products_df = cleaned_datasets["products"]

    length = products_df["product_length_cm"]
    height = products_df["product_height_cm"]
    width = products_df["product_width_cm"]
    weight = products_df["product_weight_g"]

    valid_dimensions = (
        length.gt(0)
        & height.gt(0)
        & width.gt(0)
    ).fillna(False)

    product_volume = (
        length * height * width
    ).where(valid_dimensions)

    add_business_feature(
        "products",
        "product_volume_cm3",
        product_volume,
        "FLOAT",
        "Bounding-box product volume in cubic centimeters."
    )


    valid_density = (
        product_volume.gt(0)
        & weight.gt(0)
    ).fillna(False)

    product_density = (
        weight / product_volume.where(valid_density)
    ).round(6)

    add_business_feature(
        "products",
        "product_density_g_cm3",
        product_density,
        "FLOAT",
        "Recorded product weight divided by bounding-box volume."
    )


    # ============================================================
    # 7. REVIEW FEATURES
    # ============================================================

    reviews_df = cleaned_datasets["reviews"]

    review_created = reviews_df["review_creation_date"]
    review_answered = reviews_df["review_answer_timestamp"]

    review_duration_eligible = valid_duration(
        review_created,
        review_answered
    )

    add_business_feature(
        "reviews",
        "review_response_hours",
        calculate_duration(
            review_created,
            review_answered,
            review_duration_eligible,
            unit="hours"
        ),
        "FLOAT",
        "Hours between recorded review creation and answer timestamps."
    )

    add_business_feature(
        "reviews",
        "has_written_review",
        reviews_df["review_comment_message"].notna(),
        "BOOLEAN",
        "Review contains a non-missing written message."
    )

    add_business_feature(
        "reviews",
        "has_review_title",
        reviews_df["review_comment_title"].notna(),
        "BOOLEAN",
        "Review contains a non-missing title."
    )


    rating_classification = reviews_df["review_score"].map({
        1: "negative",
        2: "negative",
        3: "neutral",
        4: "positive",
        5: "positive"
    })

    add_business_feature(
        "reviews",
        "rating_classification",
        rating_classification,
        "STRING",
        "Rating-based classification; not text-based sentiment."
    )


    # ============================================================
    # 8. MARKETING FEATURES
    # ============================================================

    leads_df = cleaned_datasets["marketing_leads"]
    deals_df = cleaned_datasets["closed_deals"]

    add_business_feature(
        "marketing_leads",
        "first_contact_year_month",
        leads_df["first_contact_date"].dt.strftime("%Y-%m"),
        "STRING",
        "Year-month of initial marketing lead contact."
    )


    # Retrieve first-contact dates at the closed-deal grain

    contact_lookup = leads_df.set_index(
        "mql_id"
    )["first_contact_date"]

    deal_contact_date = deals_df["mql_id"].map(
        contact_lookup
    )

    conversion_duration = calculate_duration(
        deal_contact_date,
        deals_df["won_date"],
        deals_df["is_valid_conversion_duration"],
        unit="days"
    )

    add_business_feature(
        "closed_deals",
        "conversion_duration_days",
        conversion_duration,
        "FLOAT",
        "Elapsed days from recorded first contact date to deal won."
    )

    add_business_feature(
        "closed_deals",
        "won_year_month",
        deals_df["won_date"].dt.strftime("%Y-%m"),
        "STRING",
        "Year-month when the marketing deal was won."
    )


    # ============================================================
    # 9. CONSOLIDATE FEATURE METADATA
    # ============================================================

    feature_engineering_df = pd.DataFrame(
        feature_records
    )

    derived_business_dictionary_df = pd.DataFrame(
        derived_business_fields
    )

    cleaning_dictionary_df = pd.concat(
        [
            cleaning_dictionary_df,
            derived_business_dictionary_df
        ],
        ignore_index=True
    )

    print("COMMERCEIQ - BUSINESS FEATURE ENGINEERING")

    display(
        feature_engineering_df[
            [
                "dataset",
                "feature",
                "analytical_type",
                "actual_dtype",
                "valid_records",
                "missing_records"
            ]
        ]
    )


    # ============================================================
    # 10. DELIVERY PERFORMANCE SUMMARY
    # ============================================================

    delivery_performance_summary_df = (
        orders_df["delivery_performance"]
        .value_counts(dropna=False)
        .rename_axis("delivery_performance")
        .reset_index(name="order_count")
    )

    print("\nDELIVERY PERFORMANCE SUMMARY")

    display(delivery_performance_summary_df)


    eligible_deliveries = int(
        orders_df["is_valid_delivery_promise_comparison"].sum()
    )

    on_time_deliveries = int(
        orders_df["is_on_time_delivery"].sum()
    )

    on_time_delivery_pct = round(
        on_time_deliveries / eligible_deliveries * 100,
        4
    ) if eligible_deliveries else None

    print("Eligible deliveries:", eligible_deliveries)
    print("On-time or early deliveries:", on_time_deliveries)
    print("On-time delivery percentage:", on_time_delivery_pct)


    # ============================================================
    # 11. DURATION FEATURE SUMMARY
    # ============================================================

    duration_feature_records = []

    for dataset_name, column in [
        ("orders", "approval_duration_hours"),
        ("orders", "processing_duration_days"),
        ("orders", "transit_duration_days"),
        ("orders", "delivery_duration_days"),
        ("orders", "estimated_delivery_days"),
        ("reviews", "review_response_hours"),
        ("closed_deals", "conversion_duration_days")
    ]:

        series = cleaned_datasets[dataset_name][column]

        duration_feature_records.append({
            "dataset": dataset_name,
            "feature": column,
            "valid_records": int(series.notna().sum()),
            "missing_records": int(series.isna().sum()),
            "minimum": series.min(),
            "mean": series.mean(),
            "median": series.median(),
            "maximum": series.max(),
            "negative_values": int(series.lt(0).sum())
        })


    duration_feature_summary_df = pd.DataFrame(
        duration_feature_records
    ).round(4)

    print("\nVALIDATED DURATION FEATURES")

    display(duration_feature_summary_df)


    # ============================================================
    # 12. FINANCIAL FEATURE RECONCILIATION
    # ============================================================

    total_merchandise_value = sum(
        items_df["price"], Decimal("0")
    )

    total_freight_value = sum(
        items_df["freight_value"], Decimal("0")
    )

    total_item_value_with_freight = sum(
        items_df["item_value_with_freight"], Decimal("0")
    )

    assert total_item_value_with_freight == (
        total_merchandise_value + total_freight_value
    )

    financial_feature_summary_df = pd.DataFrame([
        {
            "metric": "Recorded merchandise value",
            "amount_brl": total_merchandise_value
        },
        {
            "metric": "Recorded freight value",
            "amount_brl": total_freight_value
        },
        {
            "metric": "Recorded merchandise plus freight",
            "amount_brl": total_item_value_with_freight
        }
    ])

    print("\nFINANCIAL FEATURE RECONCILIATION")

    display(financial_feature_summary_df)


    # ============================================================
    # 13. RATING CLASSIFICATION SUMMARY
    # ============================================================

    rating_classification_summary_df = (
        reviews_df["rating_classification"]
        .value_counts(dropna=False)
        .rename_axis("rating_classification")
        .reset_index(name="review_count")
    )

    print("\nRATING CLASSIFICATION SUMMARY")

    display(rating_classification_summary_df)


    # ============================================================
    # 14. FINAL VALIDATION
    # ============================================================

    rows_after_features = sum(
        len(df) for df in cleaned_datasets.values()
    )

    fields_after_features = sum(
        len(df.columns) for df in cleaned_datasets.values()
    )

    assert rows_after_features == rows_before_features

    assert fields_after_features == (
        fields_before_features
        + len(derived_business_fields)
    )

    assert len(derived_business_fields) == 27

    assert len(cleaning_dictionary_df) == fields_after_features

    assert duration_feature_summary_df[
        "negative_values"
    ].eq(0).all()

    assert int(
        orders_df["is_on_time_delivery"].notna().sum()
    ) == eligible_deliveries

    assert deals_df[
        "conversion_duration_days"
    ].notna().sum() == 841

    assert products_df[
        "product_density_g_cm3"
    ].dropna().gt(0).all()

    assert items_df[
        "freight_share_of_item_total_pct"
    ].dropna().between(0, 100).all()


    print("\nFEATURE ENGINEERING SUMMARY")

    print(
        "Datasets receiving new features:",
        feature_engineering_df["dataset"].nunique()
    )

    print(
        "Business features created:",
        len(feature_engineering_df)
    )

    print(
        "Duration features validated:",
        len(duration_feature_summary_df)
    )

    print(
        "Negative duration values:",
        duration_feature_summary_df["negative_values"].sum()
    )

    print("Financial reconciliation: PASSED")

    print("Fields before:", fields_before_features)

    print("Fields after:", fields_after_features)

    print("Total working datasets:", len(cleaned_datasets))

    print("Total working rows:", f"{rows_after_features:,}")

    print("Rows removed:", rows_before_features - rows_after_features)

    print("Cleaning actions logged:", len(cleaning_log))

    print("\nStep 4.11 completed successfully.")

    # Transformation step 4.12
    # Step 4.12: Final validation and quality reconciliation


    # ============================================================
    # 1. DATASET-LEVEL RECONCILIATION
    # ============================================================

    final_dataset_records = []

    for dataset_name, df in cleaned_datasets.items():

        source_df = raw_datasets.get(dataset_name)

        original_rows_count = (
            len(source_df) if source_df is not None else 0
        )

        original_fields_count = (
            len(source_df.columns) if source_df is not None else 0
        )

        final_dataset_records.append({
            "dataset": dataset_name,
            "dataset_origin": (
                "Source-derived"
                if source_df is not None
                else "Project-derived"
            ),
            "original_rows": original_rows_count,
            "final_rows": len(df),
            "rows_added": max(
                len(df) - original_rows_count, 0
            ),
            "rows_removed": max(
                original_rows_count - len(df), 0
            ),
            "original_fields": original_fields_count,
            "final_fields": len(df.columns),
            "field_change": (
                len(df.columns) - original_fields_count
            ),
            "missing_cells": int(df.isna().sum().sum()),
            "memory_mb": round(
                df.memory_usage(deep=True).sum() / 1024**2,
                2
            )
        })


    final_dataset_summary_df = pd.DataFrame(
        final_dataset_records
    )

    print("COMMERCEIQ - FINAL DATASET SUMMARY")

    display(final_dataset_summary_df)


    # ============================================================
    # 2. FINAL PRIMARY KEY AND DUPLICATE VALIDATION
    # ============================================================

    final_key_records = []

    for dataset_name, df in cleaned_datasets.items():

        key_fields = cleaning_dictionary_df.loc[
            cleaning_dictionary_df["dataset"].eq(dataset_name)
            & cleaning_dictionary_df["primary_key_component"].eq(True),
            "column"
        ].tolist()

        assert key_fields, (
            f"Primary key definition missing: {dataset_name}"
        )

        missing_key_rows = int(
            df[key_fields].isna().any(axis=1).sum()
        )

        duplicate_key_rows = int(
            df.duplicated(subset=key_fields).sum()
        )

        # Exclude generated surrogate ID when checking
        # geographic observation duplication.

        duplicate_check_columns = (
            [
                column for column in df.columns
                if column != "geolocation_id"
            ]
            if dataset_name == "geolocation"
            else df.columns.tolist()
        )

        exact_duplicate_rows = int(
            df.duplicated(
                subset=duplicate_check_columns
            ).sum()
        )

        final_key_records.append({
            "dataset": dataset_name,
            "primary_key": " + ".join(key_fields),
            "total_rows": len(df),
            "missing_key_rows": missing_key_rows,
            "duplicate_key_rows": duplicate_key_rows,
            "exact_duplicate_rows": exact_duplicate_rows,
            "status": (
                "PASS"
                if missing_key_rows == 0
                and duplicate_key_rows == 0
                and exact_duplicate_rows == 0
                else "FAIL"
            )
        })


    final_key_validation_df = pd.DataFrame(
        final_key_records
    )

    print("\nFINAL PRIMARY KEY AND DUPLICATE VALIDATION")

    display(final_key_validation_df)


    # ============================================================
    # 3. REFRESH FINAL DATA DICTIONARY
    # ============================================================

    def get_final_cardinality(unique_count, valid_count):

        if unique_count == 0:
            return "No valid values"

        if unique_count == 1:
            return "Constant"

        if unique_count == valid_count:
            return "Unique"

        if unique_count <= 20:
            return "Low"

        if unique_count <= 100:
            return "Medium"

        return "High"


    final_field_records = []

    for dataset_name, df in cleaned_datasets.items():

        for column in df.columns:

            series = df[column]

            valid_count = int(series.notna().sum())
            missing_count = int(series.isna().sum())
            unique_count = int(series.nunique())

            final_field_records.append({
                "dataset": dataset_name,
                "column": column,
                "current_dtype": str(series.dtype),
                "converted_dtype": str(series.dtype),
                "total_records": len(series),
                "valid_records": valid_count,
                "unique_values": unique_count,
                "total_missing": missing_count,
                "missing_pct": round(
                    series.isna().mean() * 100, 4
                ),
                "completeness_pct": round(
                    series.notna().mean() * 100, 4
                ),
                "cardinality": get_final_cardinality(
                    unique_count, valid_count
                )
            })


    final_field_profile_df = pd.DataFrame(
        final_field_records
    )

    # Ensure dictionary definitions match the actual schema

    actual_schema = set(
        final_field_profile_df[
            ["dataset", "column"]
        ].itertuples(index=False, name=None)
    )

    dictionary_schema = set(
        cleaning_dictionary_df[
            ["dataset", "column"]
        ].itertuples(index=False, name=None)
    )

    assert actual_schema == dictionary_schema

    assert not cleaning_dictionary_df.duplicated(
        subset=["dataset", "column"]
    ).any()


    # Replace outdated source profiling metadata
    # with current cleaned dataset metadata.

    refresh_columns = [
        column
        for column in final_field_profile_df.columns
        if column not in ["dataset", "column"]
    ]

    final_data_dictionary_df = (
        cleaning_dictionary_df
        .drop(columns=refresh_columns, errors="ignore")
        .merge(
            final_field_profile_df,
            on=["dataset", "column"],
            how="inner",
            validate="one_to_one"
        )
    )


    # Populate consistent dataset grain definitions

    final_grain_mapping = {
        "orders": "One record per order",
        "customers": "One record per customer ID",
        "order_items": "One record per order item",
        "payments": "One record per order payment sequence",
        "reviews": "One record per review ID and order ID",
        "products": "One record per product",
        "sellers": "One record per seller",
        "geolocation": "One cleaned geographic observation",
        "category_translation": "One record per product category",
        "marketing_leads": "One record per marketing qualified lead",
        "closed_deals": "One record per recorded won marketing lead",
        "brazil_holidays": "One record per holiday date and country",
        "geolocation_lookup": "One record per eligible postal prefix"
    }

    final_data_dictionary_df["grain"] = (
        final_data_dictionary_df["dataset"]
        .map(final_grain_mapping)
    )

    final_data_dictionary_df["original_column"] = (
        final_data_dictionary_df["original_column"]
        .where(
            final_data_dictionary_df["field_origin"].eq("Source"),
            pd.NA
        )
    )

    cleaning_dictionary_df = final_data_dictionary_df.copy()


    print("\nFINAL DATA DICTIONARY SUMMARY")

    display(
        final_data_dictionary_df
        .groupby("dataset", as_index=False)
        .agg(
            total_fields=("column", "size"),
            missing_cells=("total_missing", "sum"),
            primary_key_fields=("primary_key_component", "sum")
        )
    )


    # ============================================================
    # 4. VALIDATE FINAL DATA TYPES
    # ============================================================

    expected_dtype_mapping = {
        "STRING": "string",
        "TEXT": "string",
        "JSON": "string",
        "INTEGER": "Int64",
        "FLOAT": "Float64",
        "DECIMAL": "object",
        "DATE": "datetime64[ns]",
        "DATETIME": "datetime64[ns]",
        "BOOLEAN": "boolean"
    }

    final_dtype_validation_df = final_data_dictionary_df[
        [
            "dataset",
            "column",
            "recommended_dtype",
            "current_dtype"
        ]
    ].copy()

    final_dtype_validation_df["expected_dtype"] = (
        final_dtype_validation_df["recommended_dtype"]
        .map(expected_dtype_mapping)
    )

    final_dtype_validation_df["status"] = np.where(
        final_dtype_validation_df["current_dtype"].eq(
            final_dtype_validation_df["expected_dtype"]
        ),
        "PASS",
        "FAIL"
    )

    # Confirm Decimal object columns contain actual Decimal values.

    for field in final_data_dictionary_df.loc[
        final_data_dictionary_df["recommended_dtype"].eq("DECIMAL")
    ].itertuples(index=False):

        series = cleaned_datasets[field.dataset][field.column]

        assert series.dropna().map(
            lambda value: isinstance(value, Decimal)
            and value.is_finite()
        ).all()


    print("\nFINAL DATA TYPE VALIDATION")

    display(
        final_dtype_validation_df["status"]
        .value_counts()
        .rename_axis("status")
        .reset_index(name="field_count")
    )


    # ============================================================
    # 5. RECONCILE ALL 43 DATA QUALITY OBSERVATIONS
    # ============================================================

    # RESOLVED:
    # An identified structural or representation issue was corrected.
    #
    # CONTROLLED:
    # The issue remains, but explicit flags or analytical rules
    # prevent inappropriate use.
    #
    # ACCEPTED LIMITATION:
    # Source information remains unavailable or unverifiable.
    # No unsupported correction has been applied.

    quality_treatment_mapping = {

        "DQ001": (
            "RESOLVED", "4.4, 4.9",
            "Removed 261,831 exact duplicates and "
            "17,837 post-normalization duplicates."
        ),

        "DQ002": (
            "RESOLVED", "4.9",
            "Created unique lookup containing 19,011 postal prefixes."
        ),

        "DQ003": (
            "CONTROLLED", "4.9",
            "Excluded 27 observations outside the approximate "
            "Brazil screening envelope from lookup calculations."
        ),

        "DQ004": (
            "RESOLVED", "4.6",
            "Normalized geographic city labels; "
            "full geographic accuracy is not independently verified."
        ),

        "DQ005": (
            "RESOLVED", "4.6",
            "Standardized six seller city observations."
        ),

        "DQ006": (
            "CONTROLLED", "4.5",
            "Classified 610 missing product categories as unknown."
        ),

        "DQ007": (
            "RESOLVED", "4.6",
            "Added two missing translations and an unknown mapping."
        ),

        "DQ008": (
            "CONTROLLED", "4.7",
            "Converted four zero weights to missing "
            "and retained source anomaly flags."
        ),

        "DQ009": (
            "ACCEPTED LIMITATION", "4.5, 4.11",
            "Preserved missing measurements and excluded them "
            "from dependent product calculations."
        ),

        "DQ010": (
            "ACCEPTED LIMITATION", "4.5, 4.11",
            "Preserved optional review titles and added availability flag."
        ),

        "DQ011": (
            "ACCEPTED LIMITATION", "4.5, 4.11",
            "Preserved optional review messages and added availability flag."
        ),

        "DQ012": (
            "RESOLVED", "4.4",
            "Validated review ID and order ID composite primary key."
        ),

        "DQ013": (
            "CONTROLLED", "4.4, 4.10",
            "Preserved multiple reviews per order; "
            "order-level aggregation required in downstream joins."
        ),

        "DQ014": (
            "CONTROLLED", "4.8",
            "Flagged 14 delivered orders missing approval timestamps."
        ),

        "DQ015": (
            "CONTROLLED", "4.8",
            "Flagged two delivered orders missing carrier timestamps."
        ),

        "DQ016": (
            "CONTROLLED", "4.8",
            "Flagged eight delivered orders missing delivery timestamps."
        ),

        "DQ017": (
            "CONTROLLED", "4.8",
            "Flagged 166 carrier timestamps preceding order purchase."
        ),

        "DQ018": (
            "CONTROLLED", "4.8",
            "Flagged 1,359 reversed approval-to-carrier sequences."
        ),

        "DQ019": (
            "CONTROLLED", "4.8",
            "Flagged 61 deliveries preceding order approval."
        ),

        "DQ020": (
            "CONTROLLED", "4.8",
            "Flagged 23 deliveries preceding carrier handover."
        ),

        "DQ021": (
            "CONTROLLED", "4.10",
            "Flagged 775 orders without item records."
        ),

        "DQ022": (
            "CONTROLLED", "4.10",
            "Flagged one order without payment records."
        ),

        "DQ023": (
            "ACCEPTED LIMITATION", "4.10",
            "Identified 768 orders without recorded reviews."
        ),

        "DQ024": (
            "CONTROLLED", "4.7",
            "Preserved and flagged 383 zero freight observations."
        ),

        "DQ025": (
            "CONTROLLED", "4.8",
            "Flagged four shipping deadlines exceeding "
            "the provisional 180-day threshold."
        ),

        "DQ026": (
            "CONTROLLED", "4.7",
            "Preserved and flagged two zero installment records."
        ),

        "DQ027": (
            "CONTROLLED", "4.7",
            "Preserved and flagged nine zero payment records."
        ),

        "DQ028": (
            "CONTROLLED", "4.7",
            "Preserved and flagged three undefined payment methods."
        ),

        "DQ029": (
            "CONTROLLED", "4.9, 4.10",
            "Preserved and flagged 279 unmatched customer postal prefixes."
        ),

        "DQ030": (
            "CONTROLLED", "4.9, 4.10",
            "Preserved and flagged seven unmatched seller postal prefixes."
        ),

        "DQ031": (
            "CONTROLLED", "4.5",
            "Classified 60 missing marketing origins as not_recorded."
        ),

        "DQ032": (
            "CONTROLLED", "4.8, 4.11",
            "Excluded one negative conversion duration "
            "from derived duration calculations."
        ),

        "DQ033": (
            "ACCEPTED LIMITATION", "4.10",
            "Preserved 462 closed deals without marketplace seller matches."
        ),

        "DQ034": (
            "ACCEPTED LIMITATION", "4.5",
            "Preserved 779 missing company indicators."
        ),

        "DQ035": (
            "ACCEPTED LIMITATION", "4.5",
            "Preserved 778 missing GTIN indicators."
        ),

        "DQ036": (
            "ACCEPTED LIMITATION", "4.5",
            "Preserved 776 missing average stock declarations."
        ),

        "DQ037": (
            "ACCEPTED LIMITATION", "4.5",
            "Preserved 773 missing catalog size declarations."
        ),

        "DQ038": (
            "CONTROLLED", "4.7",
            "Preserved and flagged 797 zero declared revenue values."
        ),

        "DQ039": (
            "CONTROLLED", "4.7",
            "Flagged one declared revenue value exceeding "
            "the provisional BRL 10 million threshold."
        ),

        "DQ040": (
            "RESOLVED", "4.5",
            "Removed completely empty launch_year field "
            "from the analytical copy."
        ),

        "DQ041": (
            "ACCEPTED LIMITATION", "4.3",
            "Preserved source is_fixed values. "
            "Do not use this field to infer recurring holiday dates."
        ),

        "DQ042": (
            "CONTROLLED", "4.3",
            "Preserved is_global and counties metadata. "
            "Apply regional eligibility before holiday-based analysis."
        ),

        "DQ043": (
            "CONTROLLED", "4.8",
            "Defined core reporting period containing 99,092 orders "
            "and preserved 349 boundary-period orders."
        )
    }


    # Detect issue identifier column from existing register

    issue_id_column = next(
        column for column in quality_register_df.columns
        if quality_register_df[column]
        .astype("string")
        .str.fullmatch(r"DQ\d{3}")
        .fillna(False)
        .all()
    )

    quality_treatment_mapping_df = pd.DataFrame([
        {
            issue_id_column: issue_id,
            "treatment_status": status,
            "phase4_step": step,
            "treatment_description": description
        }
        for issue_id, (
            status, step, description
        ) in quality_treatment_mapping.items()
    ])

    final_quality_register_df = quality_register_df.merge(
        quality_treatment_mapping_df,
        on=issue_id_column,
        how="left",
        validate="one_to_one"
    )

    assert len(final_quality_register_df) == 43

    assert final_quality_register_df[
        "treatment_status"
    ].notna().all()

    quality_resolution_summary_df = (
        final_quality_register_df["treatment_status"]
        .value_counts()
        .rename_axis("treatment_status")
        .reset_index(name="issue_count")
    )

    print("\nQUALITY OBSERVATION RECONCILIATION")

    display(quality_resolution_summary_df)

    print("\nQUALITY STATUS BY PRIORITY")

    quality_priority_summary_df = pd.crosstab(
        final_quality_register_df["priority"],
        final_quality_register_df["treatment_status"],
        margins=True,
        margins_name="Total"
    )

    display(quality_priority_summary_df)


    # ============================================================
    # 6. CONSOLIDATE FINAL VALIDATION CHECKS
    # ============================================================

    final_validation_records = []


    def record_validation(check_name, condition, details=""):

        final_validation_records.append({
            "validation_check": check_name,
            "status": "PASS" if bool(condition) else "FAIL",
            "details": details
        })


    source_row_count = int(
        final_dataset_summary_df["original_rows"].sum()
    )

    final_row_count = int(
        final_dataset_summary_df["final_rows"].sum()
    )

    total_removed_rows = int(
        final_dataset_summary_df["rows_removed"].sum()
    )

    total_added_rows = int(
        final_dataset_summary_df["rows_added"].sum()
    )

    final_field_count = int(
        final_dataset_summary_df["final_fields"].sum()
    )

    final_missing_count = int(
        final_dataset_summary_df["missing_cells"].sum()
    )

    record_validation(
        "Source dataset count",
        len(raw_datasets) == 12
    )

    record_validation(
        "Final dataset count",
        len(cleaned_datasets) == 13
    )

    record_validation(
        "Record count reconciliation",
        source_row_count - total_removed_rows
        + total_added_rows == final_row_count
    )

    record_validation(
        "Source business records preserved",
        all(
            len(cleaned_datasets[name]) == len(raw_datasets[name])
            for name in raw_datasets
            if name not in ["geolocation", "category_translation"]
        )
    )

    record_validation(
        "Final field count",
        final_field_count == 165
    )

    record_validation(
        "Data dictionary completeness",
        len(final_data_dictionary_df) == final_field_count
    )

    record_validation(
        "Primary key and duplicate integrity",
        final_key_validation_df["status"].eq("PASS").all()
    )

    record_validation(
        "Data type integrity",
        final_dtype_validation_df["status"].eq("PASS").all()
    )

    record_validation(
        "Required relationship integrity",
        required_relationships["status"]
        .eq("COMPLETE MATCH").all()
    )

    record_validation(
        "Optional relationship gaps documented",
        optional_relationships["status"]
        .eq("EXPECTED COVERAGE GAP").all()
    )

    record_validation(
        "Geographic join safety",
        join_validation_df["status"].eq("PASS").all()
    )

    record_validation(
        "Product category lookup coverage",
        matched_products == len(cleaned_datasets["products"])
    )

    record_validation(
        "Original financial values preserved",
        financial_preservation_df["status"]
        .eq("PRESERVED").all()
    )

    record_validation(
        "Source timestamp preservation",
        timestamp_preservation_df["status"]
        .eq("PRESERVED").all()
    )

    record_validation(
        "Derived financial feature reconciliation",
        total_item_value_with_freight
        == total_merchandise_value + total_freight_value
    )

    record_validation(
        "Non-negative eligible durations",
        duration_feature_summary_df["negative_values"].eq(0).all()
    )

    record_validation(
        "Quality issue treatment coverage",
        final_quality_register_df["treatment_status"].notna().all()
        and len(final_quality_register_df) == 43
    )

    record_validation(
        "Missing-value metadata reconciliation",
        int(final_data_dictionary_df["total_missing"].sum())
        == final_missing_count
    )

    record_validation(
        "Unique geographic lookup",
        cleaned_datasets["geolocation_lookup"][
            "zip_code_prefix"
        ].is_unique
    )

    record_validation(
        "Delivery eligibility reconciliation",
        cleaned_datasets["orders"][
            "delivery_duration_days"
        ].notna().sum()
        == cleaned_datasets["orders"][
            "is_valid_delivery_duration"
        ].sum()
    )

    final_validation_df = pd.DataFrame(
        final_validation_records
    )

    print("\nFINAL VALIDATION RESULTS")

    display(final_validation_df)


    # ============================================================
    # 7. CONSOLIDATE CLEANING ACTION LOG
    # ============================================================

    cleaning_audit_df = pd.DataFrame(cleaning_log)

    cleaning_audit_df.insert(
        0,
        "action_id",
        [
            f"CLN{i:03d}"
            for i in range(1, len(cleaning_audit_df) + 1)
        ]
    )

    print("\nCLEANING ACTION SUMMARY BY DATASET")

    display(
        cleaning_audit_df
        .groupby("dataset", as_index=False)
        .agg(
            cleaning_actions=("action_id", "count")
        )
        .sort_values("cleaning_actions", ascending=False)
    )


    # ============================================================
    # 8. FINAL PHASE 4 CLEANING SUMMARY
    # ============================================================

    final_cleaning_summary_df = pd.DataFrame([
        {"metric": "Original datasets", "value": len(raw_datasets)},
        {"metric": "Final datasets", "value": len(cleaned_datasets)},
        {"metric": "Original records", "value": source_row_count},
        {"metric": "Records removed", "value": total_removed_rows},
        {"metric": "Records added", "value": total_added_rows},
        {"metric": "Final records", "value": final_row_count},
        {"metric": "Original fields", "value": 81},
        {"metric": "Final fields", "value": final_field_count},
        {"metric": "Final missing cells", "value": final_missing_count},
        {"metric": "Quality observations reviewed", "value": 43},
        {"metric": "Cleaning actions", "value": len(cleaning_audit_df)},
        {"metric": "Validation checks", "value": len(final_validation_df)},
        {
            "metric": "Validation checks passed",
            "value": int(final_validation_df["status"].eq("PASS").sum())
        },
        {
            "metric": "Validation checks failed",
            "value": int(final_validation_df["status"].eq("FAIL").sum())
        }
    ])

    print("\nFINAL CLEANING SUMMARY")

    display(final_cleaning_summary_df)


    assert final_validation_df["status"].eq("PASS").all(), (
        "Final validation failed. Review failed checks before export."
    )

    print("\nStep 4.12 completed successfully.")
    print("All final validation checks passed.")
    print("Cleaned datasets are ready for export.")


    if export:

        processed_manifest_df, processed_schema = (
            export_processed_datasets(
                cleaned_datasets,
                final_data_dictionary_df,
                PROJECT_ROOT
            )
        )

        final_cleaning_summary_df.to_csv(
            PROJECT_ROOT / "data" / "metadata"
            / "cleaning_summary.csv",
            index=False
        )

    result = {
        "datasets": cleaned_datasets,
        "data_dictionary": final_data_dictionary_df,
        "quality_register": final_quality_register_df,
        "cleaning_summary": final_cleaning_summary_df,
        "validation_results": final_validation_df,
        "cleaning_audit": cleaning_audit_df
    }

    if return_audit:
        result["audit_tables"] = {
            "final_dataset_summary": final_dataset_summary_df,
            "final_key_validation": final_key_validation_df,
            "final_dtype_validation": final_dtype_validation_df,
            "cleaned_relationship": cleaned_relationship_df,
            "duration_feature_summary": duration_feature_summary_df,
            "delivery_performance_summary": delivery_performance_summary_df,
            "rating_classification_summary": rating_classification_summary_df,
            "quality_resolution_summary": quality_resolution_summary_df,
            "financial_preservation": financial_preservation_df,
            "geographic_summary": geographic_summary_df,
            "join_validation": join_validation_df,
        }

    return result


if __name__ == "__main__":

    run_cleaning(export=True)
