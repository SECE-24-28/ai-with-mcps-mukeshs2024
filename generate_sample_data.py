"""
Generate realistic sample e-commerce sales data for testing the multi-agent pipeline.
Creates ~500 rows with intentional data quality issues for the cleaner agent.
"""

import csv
import os
import random
from datetime import datetime, timedelta

# Configuration
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sample_sales_data.csv")
NUM_ROWS = 500

# Data pools
PRODUCTS = {
    "Widget A": ("Electronics", 49.99),
    "Gadget B": ("Electronics", 74.50),
    "Tool C": ("Hardware", 24.99),
    "Sensor D": ("Electronics", 129.99),
    "Cable E": ("Accessories", 9.99),
    "Mount F": ("Hardware", 34.99),
    "Adapter G": ("Accessories", 14.99),
    "Display H": ("Electronics", 199.99),
    "Bracket I": ("Hardware", 19.99),
    "Charger J": ("Accessories", 29.99),
}

REGIONS = ["North", "South", "East", "West"]
REGION_WEIGHTS = [0.40, 0.28, 0.15, 0.17]  # North dominant

CUSTOMER_TYPES = ["Retail", "Wholesale"]
CUSTOMER_WEIGHTS = [0.65, 0.35]

PAYMENT_METHODS = ["Credit Card", "Bank Transfer", "PayPal", "Cash"]
PAYMENT_WEIGHTS = [0.45, 0.25, 0.20, 0.10]


def random_date(start: datetime, end: datetime) -> str:
    """Generate a random date between start and end."""
    delta = end - start
    random_days = random.randint(0, delta.days)
    date = start + timedelta(days=random_days)
    return date.strftime("%Y-%m-%d")


def weighted_choice(items, weights):
    """Pick a random item with the given probability weights."""
    return random.choices(items, weights=weights, k=1)[0]


def generate_row(row_index: int, start_date: datetime, end_date: datetime) -> list:
    """Generate a single data row, occasionally injecting quality issues."""
    product_name = random.choice(list(PRODUCTS.keys()))
    category, base_price = PRODUCTS[product_name]
    region = weighted_choice(REGIONS, REGION_WEIGHTS)
    customer_type = weighted_choice(CUSTOMER_TYPES, CUSTOMER_WEIGHTS)
    payment = weighted_choice(PAYMENT_METHODS, PAYMENT_WEIGHTS)
    date = random_date(start_date, end_date)

    # Wholesale customers buy more
    if customer_type == "Wholesale":
        quantity = random.randint(10, 50)
    else:
        quantity = random.randint(1, 15)

    # Price variation (+/- 10%)
    unit_price = round(base_price * random.uniform(0.9, 1.1), 2)
    total_sales = round(unit_price * quantity, 2)

    # --- Inject data quality issues (roughly 5% of rows) ---

    # Missing product name (~1%)
    if random.random() < 0.01:
        product_name = ""

    # Missing total sales (~2%)
    if random.random() < 0.02:
        total_sales = ""

    # Duplicate row flag (we'll handle actual duplicates below)

    # Outlier: extremely high quantity (~1%)
    if random.random() < 0.01:
        quantity = random.randint(200, 500)
        if total_sales != "":
            total_sales = round(unit_price * quantity, 2)

    # Inconsistent text casing (~2%)
    if random.random() < 0.02:
        region = region.upper()
    if random.random() < 0.02:
        customer_type = customer_type.lower()

    # Extra whitespace in product name (~1%)
    if random.random() < 0.01 and product_name:
        product_name = f"  {product_name}  "

    return [
        date,
        product_name,
        category,
        unit_price,
        quantity,
        total_sales,
        region,
        customer_type,
        payment,
    ]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 6, 30)

    headers = [
        "Date",
        "Product_Name",
        "Category",
        "Unit_Price",
        "Quantity_Sold",
        "Total_Sales",
        "Region",
        "Customer_Type",
        "Payment_Method",
    ]

    rows = []
    for i in range(NUM_ROWS):
        rows.append(generate_row(i, start_date, end_date))

    # Inject ~5 exact duplicate rows
    for _ in range(5):
        dup_index = random.randint(0, len(rows) - 1)
        insert_pos = random.randint(0, len(rows))
        rows.insert(insert_pos, list(rows[dup_index]))

    # Inject ~3 completely empty rows
    for _ in range(3):
        insert_pos = random.randint(0, len(rows))
        rows.insert(insert_pos, [""] * len(headers))

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"[OK] Generated {len(rows)} rows of sample data")
    print(f"[->] Saved to: {OUTPUT_FILE}")
    print(f"\nData includes intentional quality issues:")
    print(f"  * ~5 duplicate rows")
    print(f"  * ~3 empty rows")
    print(f"  * ~1% missing product names")
    print(f"  * ~2% missing total sales")
    print(f"  * ~1% outlier quantities (200-500)")
    print(f"  * ~2% inconsistent text casing")
    print(f"  * ~1% extra whitespace in names")


if __name__ == "__main__":
    main()
