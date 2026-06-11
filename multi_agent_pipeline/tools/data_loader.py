"""
Data Loader Tools — Reads CSV files and extracts metadata.

These tools are used by the Data Loader Agent to read data from CSV files,
extract column metadata, detect data types, count missing values, and
provide data previews.
"""

import csv
import json
import os
from collections import Counter


def _detect_type(values: list[str]) -> str:
    """Detect the predominant data type of a list of string values."""
    type_counts = Counter()
    for v in values:
        v = v.strip()
        if not v:
            continue
        # Try boolean
        if v.lower() in ("true", "false", "yes", "no", "1", "0"):
            type_counts["boolean"] += 1
            continue
        # Try numeric (handle currency symbols)
        cleaned = v.replace("$", "").replace(",", "").replace("€", "").replace("£", "")
        try:
            float(cleaned)
            type_counts["numeric"] += 1
            continue
        except ValueError:
            pass
        # Try date patterns
        date_patterns = ["-", "/"]
        if any(sep in v for sep in date_patterns) and len(v) >= 8:
            parts = v.replace("/", "-").split("-")
            if len(parts) == 3 and all(p.strip().isdigit() for p in parts):
                type_counts["date"] += 1
                continue
        # Default: text
        type_counts["text"] += 1

    if not type_counts:
        return "text"

    most_common = type_counts.most_common(1)[0][0]
    total = sum(type_counts.values())
    # If more than 20% of values are a different type, mark as mixed
    if type_counts.most_common(1)[0][1] / total < 0.8:
        return "mixed"
    return most_common


def load_csv_file(file_path: str) -> dict:
    """Load a CSV file, extract metadata, detect data types, and assess quality.

    Args:
        file_path: Absolute or relative path to the CSV file.

    Returns:
        A dictionary containing status, metadata (columns, types, missing values),
        data preview, detected issues, data quality score, and the raw data.
    """
    # Resolve relative paths from project root
    if not os.path.isabs(file_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, file_path)

    if not os.path.exists(file_path):
        return json.dumps({
            "status": "error",
            "message": f"Cannot load file: File not found at path '{file_path}'",
            "suggestion": "Verify the file path and try again. Use 'data/sample_sales_data.csv' for the sample dataset.",
        })

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            raw_rows = [row for row in reader]
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error reading file: {str(e)}",
            "suggestion": "Ensure the file is a valid CSV with UTF-8 encoding.",
        })

    total_rows = len(raw_rows)
    total_columns = len(headers)

    # Analyze each column
    columns_meta = []
    issues = []
    total_missing = 0

    for col_idx, col_name in enumerate(headers):
        col_values = [row[col_idx] if col_idx < len(row) else "" for row in raw_rows]
        missing_count = sum(1 for v in col_values if not v.strip())
        missing_pct = round((missing_count / total_rows) * 100, 2) if total_rows > 0 else 0
        total_missing += missing_count

        non_empty = [v for v in col_values if v.strip()]
        detected_type = _detect_type(non_empty[:200])  # Sample first 200 for type detection
        sample_values = non_empty[:5]

        columns_meta.append({
            "name": col_name.strip(),
            "type": detected_type,
            "missing_count": missing_count,
            "missing_percentage": missing_pct,
            "sample_values": sample_values,
        })

        if missing_count > 0:
            issues.append(f"{missing_count} rows ({missing_pct}%) have missing '{col_name}' values")

    # Check for empty rows
    empty_rows = sum(1 for row in raw_rows if all(not v.strip() for v in row))
    if empty_rows > 0:
        issues.append(f"{empty_rows} completely empty rows detected")

    # Check for potential duplicates (exact row match)
    row_strs = ["|".join(row) for row in raw_rows]
    dup_count = len(row_strs) - len(set(row_strs))
    if dup_count > 0:
        issues.append(f"{dup_count} potential duplicate rows detected")

    # Calculate quality score
    total_cells = total_rows * total_columns if total_columns > 0 else 1
    missing_ratio = total_missing / total_cells
    dup_ratio = dup_count / total_rows if total_rows > 0 else 0
    empty_ratio = empty_rows / total_rows if total_rows > 0 else 0
    quality_score = max(0, round(100 * (1 - missing_ratio - dup_ratio - empty_ratio)))

    # Data preview (first 5 rows)
    preview = [headers] + raw_rows[:5]

    recommendation = "Proceed with cleaning" if quality_score >= 50 else "Investigate issues first — data quality is low"

    result = {
        "status": "success",
        "metadata": {
            "total_rows": total_rows,
            "total_columns": total_columns,
            "columns": columns_meta,
        },
        "data_preview": preview,
        "issues_detected": issues if issues else ["No issues detected"],
        "data_quality_score": quality_score,
        "recommendation": recommendation,
        "file_path": file_path,
    }

    return json.dumps(result, indent=2)


def get_data_preview(file_path: str, num_rows: int = 10) -> dict:
    """Get a preview of the first N rows of a CSV file.

    Args:
        file_path: Path to the CSV file.
        num_rows: Number of rows to preview (default 10).

    Returns:
        A dictionary with headers and the first N data rows.
    """
    if not os.path.isabs(file_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, file_path)

    if not os.path.exists(file_path):
        return json.dumps({
            "status": "error",
            "message": f"File not found: {file_path}",
        })

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = []
            for i, row in enumerate(reader):
                if i >= num_rows:
                    break
                rows.append(row)

        return json.dumps({
            "status": "success",
            "headers": headers,
            "preview_rows": rows,
            "rows_shown": len(rows),
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error reading file: {str(e)}",
        })
