"""
Data Cleaner Tools — Cleans and standardizes raw CSV data.

Applies a comprehensive cleaning pipeline: removes empty rows, handles
missing values, removes duplicates, standardizes data types, detects
outliers, and saves the cleaned output.
"""

import csv
import json
import os
import statistics
from collections import Counter
from datetime import datetime


def _is_numeric(value: str) -> bool:
    """Check if a string value can be parsed as a number."""
    try:
        cleaned = value.strip().replace("$", "").replace(",", "").replace("€", "").replace("£", "")
        float(cleaned)
        return True
    except (ValueError, AttributeError):
        return False


def _to_float(value: str) -> float:
    """Convert a string to float, stripping currency symbols."""
    return float(value.strip().replace("$", "").replace(",", "").replace("€", "").replace("£", ""))


def _compute_z_scores(values: list[float]) -> list[float]:
    """Compute Z-scores for a list of numeric values."""
    if len(values) < 2:
        return [0.0] * len(values)
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    if stdev == 0:
        return [0.0] * len(values)
    return [(v - mean) / stdev for v in values]


def clean_data(file_path: str) -> dict:
    """Clean a CSV file by applying a full data cleaning pipeline.

    Cleaning steps (in order):
    1. Remove completely empty rows and rows with >80% missing values
    2. Handle missing values (median for numeric, 'Unknown' for text)
    3. Remove exact duplicate rows
    4. Standardize text (trim whitespace, consistent casing)
    5. Standardize numeric formats (strip currency symbols)
    6. Detect outliers (Z-score > 3) and flag them
    7. Save cleaned data to output/cleaned_data.csv

    Args:
        file_path: Path to the CSV file to clean.

    Returns:
        A JSON string with cleaning summary, quality metrics, and output path.
    """
    # Resolve path
    if not os.path.isabs(file_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, file_path)

    if not os.path.exists(file_path):
        return json.dumps({
            "status": "error",
            "message": f"File not found: {file_path}",
            "suggestion": "Run the data loader first to verify the file path.",
        })

    # Read data
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = [h.strip() for h in next(reader)]
        raw_rows = [row for row in reader]

    rows_before = len(raw_rows)
    cols_before = len(headers)
    changes_log = {}

    # ── Step 1: Remove empty rows & rows with >80% missing ──
    cleaned_rows = []
    rows_dropped_empty = 0
    for row in raw_rows:
        # Pad rows to match header length
        while len(row) < len(headers):
            row.append("")
        non_empty = sum(1 for v in row if v.strip())
        if non_empty == 0:
            rows_dropped_empty += 1
            continue
        if non_empty / len(headers) < 0.2:
            rows_dropped_empty += 1
            continue
        cleaned_rows.append(row)
    changes_log["empty_rows_removed"] = rows_dropped_empty

    # ── Step 2: Detect column types ──
    col_types = {}
    for col_idx, col_name in enumerate(headers):
        col_values = [row[col_idx].strip() for row in cleaned_rows if row[col_idx].strip()]
        numeric_count = sum(1 for v in col_values if _is_numeric(v))
        ratio = numeric_count / len(col_values) if col_values else 0
        col_types[col_name] = "numeric" if ratio > 0.8 else "text"

    # ── Step 3: Handle missing values ──
    null_handling = {}
    for col_idx, col_name in enumerate(headers):
        col_values = [row[col_idx].strip() for row in cleaned_rows]
        missing_count = sum(1 for v in col_values if not v)
        if missing_count == 0:
            continue
        missing_pct = missing_count / len(col_values)

        if col_types[col_name] == "numeric":
            numeric_vals = [_to_float(v) for v in col_values if v and _is_numeric(v)]
            if missing_pct > 0.5:
                # Drop column (mark for exclusion)
                null_handling[col_name] = {"method": "column_dropped", "count": missing_count}
            elif numeric_vals:
                fill_val = round(statistics.median(numeric_vals), 2) if missing_pct < 0.1 else round(statistics.mean(numeric_vals), 2)
                method = "median" if missing_pct < 0.1 else "mean"
                filled = 0
                for row in cleaned_rows:
                    if not row[col_idx].strip():
                        row[col_idx] = str(fill_val)
                        filled += 1
                null_handling[col_name] = {"method": method, "count": filled, "fill_value": fill_val}
        else:
            fill_val = "Unknown" if missing_pct < 0.2 else "Other"
            filled = 0
            for row in cleaned_rows:
                if not row[col_idx].strip():
                    row[col_idx] = fill_val
                    filled += 1
            null_handling[col_name] = {"method": fill_val, "count": filled}
    changes_log["null_values_handled"] = null_handling

    # ── Step 4: Remove exact duplicate rows ──
    seen = set()
    deduped_rows = []
    duplicates_removed = 0
    for row in cleaned_rows:
        row_key = tuple(v.strip() for v in row)
        if row_key in seen:
            duplicates_removed += 1
            continue
        seen.add(row_key)
        deduped_rows.append(row)
    cleaned_rows = deduped_rows
    changes_log["duplicates_removed"] = duplicates_removed

    # ── Step 5: Standardize text ──
    text_standardized = 0
    text_cols = [i for i, (_, t) in enumerate(col_types.items()) if t == "text"]
    for row in cleaned_rows:
        for col_idx in text_cols:
            original = row[col_idx]
            cleaned = original.strip()
            # Consistent title case for known categorical fields
            if headers[col_idx] in ("Region", "Customer_Type", "Category", "Payment_Method"):
                cleaned = cleaned.title()
            if cleaned != original:
                row[col_idx] = cleaned
                text_standardized += 1
    changes_log["text_standardized"] = text_standardized

    # ── Step 6: Standardize numeric values ──
    type_conversions = {}
    for col_idx, col_name in enumerate(headers):
        if col_types[col_name] == "numeric":
            converted = 0
            for row in cleaned_rows:
                val = row[col_idx].strip()
                if val and any(c in val for c in "$,€£"):
                    row[col_idx] = str(_to_float(val))
                    converted += 1
            if converted > 0:
                type_conversions[col_name] = f"currency_text → numeric ({converted} values)"
    changes_log["data_type_conversions"] = type_conversions

    # ── Step 7: Detect outliers ──
    outliers_detected = 0
    outlier_details = {}
    for col_idx, col_name in enumerate(headers):
        if col_types[col_name] != "numeric":
            continue
        numeric_vals = []
        for row in cleaned_rows:
            try:
                numeric_vals.append(_to_float(row[col_idx]))
            except (ValueError, IndexError):
                numeric_vals.append(0.0)

        z_scores = _compute_z_scores(numeric_vals)
        col_outliers = sum(1 for z in z_scores if abs(z) > 3)
        if col_outliers > 0:
            outlier_details[col_name] = col_outliers
            outliers_detected += col_outliers
    changes_log["outliers_detected"] = outliers_detected
    changes_log["outlier_details"] = outlier_details

    # ── Step 8: Drop columns that are >50% missing (marked above) ──
    cols_to_drop = [name for name, info in null_handling.items() if info.get("method") == "column_dropped"]
    if cols_to_drop:
        drop_indices = [headers.index(name) for name in cols_to_drop if name in headers]
        headers = [h for i, h in enumerate(headers) if i not in drop_indices]
        cleaned_rows = [[v for i, v in enumerate(row) if i not in drop_indices] for row in cleaned_rows]

    # ── Save cleaned data ──
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "cleaned_data.csv")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(cleaned_rows)

    # ── Quality metrics ──
    total_cells = len(cleaned_rows) * len(headers) if headers else 1
    remaining_missing = 0
    for col_idx in range(len(headers)):
        remaining_missing += sum(1 for row in cleaned_rows if not row[col_idx].strip())
    missing_pct = round((remaining_missing / total_cells) * 100, 2)
    quality_score = max(0, round(100 - missing_pct - (outliers_detected / max(len(cleaned_rows), 1)) * 10))

    result = {
        "status": "success",
        "summary": {
            "rows_before": rows_before,
            "rows_after": len(cleaned_rows),
            "rows_dropped": rows_before - len(cleaned_rows),
            "columns_before": cols_before,
            "columns_after": len(headers),
            "columns_dropped": cols_to_drop,
        },
        "changes_made": changes_log,
        "data_quality_metrics": {
            "missing_value_percentage": missing_pct,
            "duplicate_row_percentage": round((duplicates_removed / rows_before) * 100, 2) if rows_before else 0,
            "data_type_consistency": 100 - missing_pct,
            "overall_quality_score": quality_score,
        },
        "output_file": output_path,
        "warnings": [
            f"{outliers_detected} outliers detected but preserved (analyst will decide)",
        ] if outliers_detected > 0 else [],
    }

    return json.dumps(result, indent=2)
