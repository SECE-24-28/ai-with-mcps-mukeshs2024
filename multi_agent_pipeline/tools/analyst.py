"""
Analyst Tools — Performs statistical analysis and generates insights.

Calculates descriptive statistics, correlation analysis, identifies trends,
top performers, and produces actionable recommendations from cleaned data.
"""

import csv
import json
import math
import os
import statistics
from collections import Counter, defaultdict


def _to_float_safe(value: str) -> float | None:
    """Safely convert a string to float, returning None on failure."""
    try:
        cleaned = str(value).strip().replace("$", "").replace(",", "").replace("€", "").replace("£", "")
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _percentile(sorted_data: list[float], p: float) -> float:
    """Calculate the p-th percentile from sorted data."""
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)


def _correlation(x: list[float], y: list[float]) -> float:
    """Calculate Pearson correlation coefficient between two lists."""
    n = len(x)
    if n < 3:
        return 0.0
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denom_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    denom_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
    if denom_x == 0 or denom_y == 0:
        return 0.0
    return round(numerator / (denom_x * denom_y), 4)


def analyze_data(file_path: str) -> dict:
    """Perform comprehensive statistical analysis on cleaned CSV data.

    Analysis includes:
    - Descriptive statistics for all numeric columns
    - Value counts and distributions for categorical columns
    - Correlation analysis between numeric columns
    - Identification of top performers
    - Trend detection for time-series data
    - Actionable recommendations

    Args:
        file_path: Path to the cleaned CSV file (typically output/cleaned_data.csv).

    Returns:
        A JSON string with complete analysis results.
    """
    # Resolve path
    if not os.path.isabs(file_path):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, file_path)

    if not os.path.exists(file_path):
        return json.dumps({
            "status": "error",
            "message": f"File not found: {file_path}",
            "suggestion": "Run the data cleaner first. The cleaned file is usually at 'output/cleaned_data.csv'.",
        })

    # Read data
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = [row for row in reader]

    total_records = len(rows)

    # ── Classify columns ──
    numeric_cols = []
    categorical_cols = []
    date_cols = []

    for col in headers:
        values = [row[col].strip() for row in rows if row[col].strip()]
        if not values:
            continue
        numeric_count = sum(1 for v in values if _to_float_safe(v) is not None)
        ratio = numeric_count / len(values)
        if ratio > 0.8:
            numeric_cols.append(col)
        elif col.lower() in ("date", "start_date", "end_date", "order_date"):
            date_cols.append(col)
        else:
            categorical_cols.append(col)

    # ── Phase 1: Descriptive Statistics (Numeric) ──
    numeric_stats = []
    numeric_data = {}  # For correlation analysis
    for col in numeric_cols:
        values = [_to_float_safe(row[col]) for row in rows]
        values = [v for v in values if v is not None]
        numeric_data[col] = values

        if not values:
            continue

        sorted_vals = sorted(values)
        stats = {
            "name": col,
            "count": len(values),
            "mean": round(statistics.mean(values), 2),
            "median": round(statistics.median(values), 2),
            "std": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "sum": round(sum(values), 2),
            "percentiles": {
                "25": round(_percentile(sorted_vals, 25), 2),
                "50": round(_percentile(sorted_vals, 50), 2),
                "75": round(_percentile(sorted_vals, 75), 2),
            },
        }
        numeric_stats.append(stats)

    # ── Phase 1: Descriptive Statistics (Categorical) ──
    categorical_stats = []
    for col in categorical_cols:
        values = [row[col].strip() for row in rows if row[col].strip()]
        counter = Counter(values)
        total = len(values)
        top_5 = [
            {
                "value": val,
                "count": count,
                "percentage": round((count / total) * 100, 1),
            }
            for val, count in counter.most_common(5)
        ]
        categorical_stats.append({
            "name": col,
            "unique_values": len(counter),
            "top_5": top_5,
        })

    # ── Phase 2: Correlation Analysis ──
    correlations = []
    numeric_col_names = list(numeric_data.keys())
    for i in range(len(numeric_col_names)):
        for j in range(i + 1, len(numeric_col_names)):
            col_a = numeric_col_names[i]
            col_b = numeric_col_names[j]
            # Align data (use rows where both have values)
            pairs = []
            for row in rows:
                va = _to_float_safe(row[col_a])
                vb = _to_float_safe(row[col_b])
                if va is not None and vb is not None:
                    pairs.append((va, vb))
            if len(pairs) < 3:
                continue
            x_vals, y_vals = zip(*pairs)
            corr = _correlation(list(x_vals), list(y_vals))
            strength = "strong" if abs(corr) > 0.7 else "moderate" if abs(corr) > 0.4 else "weak"
            direction = "positive" if corr > 0 else "negative"
            correlations.append({
                "column1": col_a,
                "column2": col_b,
                "correlation": corr,
                "interpretation": f"{strength} {direction} correlation ({corr})",
            })

    # Sort by absolute correlation value
    correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    # ── Phase 3: Trend Detection (if Date column exists) ──
    trends = []
    if date_cols and numeric_cols:
        date_col = date_cols[0]
        # Group by month if dates exist
        monthly_data = defaultdict(lambda: defaultdict(list))
        for row in rows:
            date_str = row.get(date_col, "").strip()
            if not date_str:
                continue
            try:
                month_key = date_str[:7]  # YYYY-MM
                for nc in numeric_cols:
                    val = _to_float_safe(row[nc])
                    if val is not None:
                        monthly_data[nc][month_key].append(val)
            except (ValueError, IndexError):
                continue

        for nc, month_map in monthly_data.items():
            sorted_months = sorted(month_map.keys())
            if len(sorted_months) < 2:
                continue
            monthly_totals = [(m, sum(month_map[m])) for m in sorted_months]
            first_total = monthly_totals[0][1]
            last_total = monthly_totals[-1][1]
            if first_total > 0:
                growth_pct = round(((last_total - first_total) / first_total) * 100, 1)
                direction = "increasing" if growth_pct > 5 else "decreasing" if growth_pct < -5 else "stable"
                trends.append({
                    "column": nc,
                    "direction": direction,
                    "growth_percentage": growth_pct,
                    "period": f"{sorted_months[0]} to {sorted_months[-1]}",
                    "first_period_total": round(first_total, 2),
                    "last_period_total": round(last_total, 2),
                })

    # ── Phase 4: Top Performers ──
    top_performers = {}

    # Find highest-value numeric column (likely revenue/sales)
    revenue_col = None
    for col in numeric_cols:
        if any(kw in col.lower() for kw in ("sales", "revenue", "total", "amount", "cost")):
            revenue_col = col
            break
    if not revenue_col and numeric_cols:
        revenue_col = numeric_cols[0]

    if revenue_col:
        total_revenue = sum(v for v in numeric_data.get(revenue_col, []) if v is not None)
        top_performers["total_revenue_column"] = revenue_col
        top_performers["total_revenue"] = round(total_revenue, 2)

        # Top category/region if categorical columns exist
        for cat_col in categorical_cols:
            cat_totals = defaultdict(float)
            for row in rows:
                cat_val = row[cat_col].strip()
                num_val = _to_float_safe(row[revenue_col])
                if cat_val and num_val is not None:
                    cat_totals[cat_val] += num_val
            if cat_totals:
                sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
                top_performers[f"top_{cat_col.lower()}"] = {
                    "value": sorted_cats[0][0],
                    "total": round(sorted_cats[0][1], 2),
                    "percentage": round((sorted_cats[0][1] / total_revenue) * 100, 1) if total_revenue else 0,
                }
                if len(sorted_cats) > 1:
                    top_performers[f"bottom_{cat_col.lower()}"] = {
                        "value": sorted_cats[-1][0],
                        "total": round(sorted_cats[-1][1], 2),
                        "percentage": round((sorted_cats[-1][1] / total_revenue) * 100, 1) if total_revenue else 0,
                    }

    # ── Phase 5: Generate Insights & Recommendations ──
    key_insights = []
    recommendations = []

    # Insight: Total records
    key_insights.append({
        "insight": f"Dataset contains {total_records} records across {len(headers)} columns",
        "metric": "Dataset Size",
        "value": f"{total_records} rows, {len(headers)} columns",
        "significance": "Sufficient data for meaningful analysis",
    })

    # Insight from top performers
    for cat_col in categorical_cols[:3]:
        key_name = f"top_{cat_col.lower()}"
        if key_name in top_performers and revenue_col:
            top = top_performers[key_name]
            key_insights.append({
                "insight": f"{top['value']} leads in {cat_col} with {top['percentage']}% of total {revenue_col}",
                "metric": f"{cat_col} Performance",
                "value": f"{top['value']}: ${top['total']:,.2f}",
                "significance": f"Key driver — focus resources on {top['value']}",
            })

            bottom_key = f"bottom_{cat_col.lower()}"
            if bottom_key in top_performers:
                bottom = top_performers[bottom_key]
                recommendations.append({
                    "priority": "Medium",
                    "recommendation": f"Investigate underperformance in {bottom['value']} ({cat_col})",
                    "expected_impact": f"Could increase share from {bottom['percentage']}% if improved",
                    "based_on": f"{bottom['value']} has lowest {revenue_col} in {cat_col} analysis",
                })

    # Insight from trends
    for trend in trends[:3]:
        key_insights.append({
            "insight": f"{trend['column']} shows {trend['direction']} trend ({trend['growth_percentage']:+.1f}%)",
            "metric": "Trend Analysis",
            "value": f"{trend['period']}: {trend['growth_percentage']:+.1f}%",
            "significance": "Monitor this trend for strategic decisions",
        })
        if trend["direction"] == "decreasing":
            recommendations.append({
                "priority": "High",
                "recommendation": f"Address declining {trend['column']} trend",
                "expected_impact": f"Reverse {abs(trend['growth_percentage']):.1f}% decline",
                "based_on": f"{trend['column']} decreased from ${trend['first_period_total']:,.0f} to ${trend['last_period_total']:,.0f}",
            })

    # Insight from strong correlations
    for corr in correlations[:2]:
        if abs(corr["correlation"]) > 0.4:
            key_insights.append({
                "insight": f"{corr['interpretation']} between {corr['column1']} and {corr['column2']}",
                "metric": "Correlation",
                "value": f"r = {corr['correlation']}",
                "significance": f"Changes in {corr['column1']} are linked to changes in {corr['column2']}",
            })

    # Default recommendation if none generated
    if not recommendations:
        recommendations.append({
            "priority": "Medium",
            "recommendation": "Continue monitoring key metrics and collect more data",
            "expected_impact": "Better trend visibility over time",
            "based_on": "Current analysis shows stable patterns",
        })

    # ── Build result ──
    result = {
        "status": "success",
        "summary_statistics": {
            "total_records": total_records,
            "total_columns": len(headers),
            "numeric_columns": numeric_stats,
            "categorical_columns": categorical_stats,
        },
        "correlations": correlations[:10],
        "trends": trends,
        "key_insights": key_insights,
        "top_performers": top_performers,
        "recommendations": recommendations,
        "warnings": [],
    }

    # Add warnings
    if total_records < 100:
        result["warnings"].append("Small dataset — statistical findings may not be robust")
    if not date_cols:
        result["warnings"].append("No date column detected — trend analysis not available")

    return json.dumps(result, indent=2)
