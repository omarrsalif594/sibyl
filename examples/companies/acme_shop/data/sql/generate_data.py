#!/usr/bin/env python3
"""
Generate synthetic e-commerce data for Acme Shop.

Creates SQLite database with:
- 30 products across 5 categories
- 4 customers
- 1000 orders over 24 months
- Realistic seasonality (camping gear peaks in summer)
"""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Seed for reproducibility
random.seed(42)

# Database path
DB_PATH = Path(__file__).parent / "acme_shop.db"

# Categories and their seasonal patterns
CATEGORIES = {
    "Camping": {"base_demand": 100, "summer_boost": 2.5, "winter_drop": 0.4},
    "Apparel": {"base_demand": 120, "summer_boost": 1.3, "winter_drop": 1.1},
    "Footwear": {"base_demand": 80, "summer_boost": 1.6, "winter_drop": 0.7},
    "Backpacks": {"base_demand": 90, "summer_boost": 1.8, "winter_drop": 0.6},
    "Accessories": {"base_demand": 70, "summer_boost": 1.4, "winter_drop": 0.8},
}

# Products (name, code, category, price)
PRODUCTS = [
    # Camping
    ("Summit Pro 3-Person Tent", "SP-TENT-003", "Camping", 349.99),
    ("Arctic Sleep 20F Down Sleeping Bag", "AS-SLEEP-20", "Camping", 279.99),
    ("Arctic Sleep 40F Synthetic Bag", "AS-SLEEP-40", "Camping", 129.99),
    ("FlowPure Water Filter System", "FP-FILTER-02", "Camping", 59.99),
    ("Ultralight 2-Person Tent", "UL-TENT-002", "Camping", 299.99),
    ("Camping Stove Pro", "CS-STOVE-01", "Camping", 89.99),
    ("Insulated Sleeping Pad", "ISP-PAD-01", "Camping", 119.99),
    # Apparel
    ("Alpine Trail Hoodie", "AT-HDIE-001", "Apparel", 89.99),
    ("Merino Comfort Base Layer Top", "MC-BASE-L01", "Apparel", 79.99),
    ("Merino Base Layer Bottom", "MC-BASE-L02", "Apparel", 74.99),
    ("Rain Shell Jacket", "RS-JACK-01", "Apparel", 189.99),
    ("Convertible Hiking Pants", "CH-PANT-01", "Apparel", 84.99),
    ("Performance T-Shirt", "PT-SHRT-01", "Apparel", 34.99),
    ("Insulated Puffy Jacket", "IP-JACK-02", "Apparel", 229.99),
    ("Fleece Pullover", "FP-PULL-01", "Apparel", 69.99),
    # Footwear
    ("TrailBlazer Waterproof Hiking Boots", "TB-BOOT-MID", "Footwear", 189.99),
    ("Summit Trail Running Shoes", "ST-RUN-01", "Footwear", 139.99),
    ("Camp Sandals", "CS-SAND-01", "Footwear", 49.99),
    ("Winter Insulated Boots", "WI-BOOT-01", "Footwear", 219.99),
    ("Approach Shoes", "AP-SHOE-01", "Footwear", 159.99),
    # Backpacks
    ("TrailRunner 25L Backpack", "TR-PACK-025", "Backpacks", 129.99),
    ("Expedition 65L Backpack", "EX-PACK-065", "Backpacks", 249.99),
    ("Daypack 18L", "DP-PACK-018", "Backpacks", 79.99),
    ("Ultralight Summit Pack 35L", "US-PACK-035", "Backpacks", 189.99),
    ("Hydration Pack 12L", "HP-PACK-012", "Backpacks", 89.99),
    # Accessories
    ("Carbon Summit Trekking Poles", "CS-POLE-PRO", "Accessories", 149.99),
    ("Headlamp Ultra", "HL-ULTRA-01", "Accessories", 64.99),
    ("Navigation GPS Device", "NG-GPS-01", "Accessories", 299.99),
    ("Quick-Dry Towel", "QD-TOWEL-01", "Accessories", 24.99),
    ("Bear Canister", "BC-CAN-01", "Accessories", 79.99),
]

# Customer data
CUSTOMERS = [
    ("Sarah Johnson", "sarah.j@email.com", "Seattle", "WA"),
    ("Michael Chen", "m.chen@email.com", "Denver", "CO"),
    ("Emily Rodriguez", "emily.r@email.com", "Portland", "OR"),
    ("David Park", "david.park@email.com", "Boulder", "CO"),
]


def create_schema(conn) -> None:
    """Create database schema."""
    cursor = conn.cursor()

    # Categories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    """)

    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        )
    """)

    # Customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            city TEXT,
            state TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            order_date TIMESTAMP NOT NULL,
            subtotal REAL NOT NULL,
            tax REAL NOT NULL,
            shipping REAL NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'completed',
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)

    # Order items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            line_total REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    conn.commit()


def insert_categories(conn) -> None:
    """Insert product categories."""
    cursor = conn.cursor()
    for cat_name in CATEGORIES:
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (cat_name,))
    conn.commit()


def insert_products(conn) -> None:
    """Insert products."""
    cursor = conn.cursor()

    # Get category IDs
    cursor.execute("SELECT category_id, name FROM categories")
    cat_map = {name: cat_id for cat_id, name in cursor.fetchall()}

    for name, code, category, price in PRODUCTS:
        cursor.execute(
            """
            INSERT INTO products (product_code, name, category_id, price)
            VALUES (?, ?, ?, ?)
            """,
            (code, name, cat_map[category], price),
        )

    conn.commit()


def insert_customers(conn) -> None:
    """Insert customers."""
    cursor = conn.cursor()
    for name, email, city, state in CUSTOMERS:
        cursor.execute(
            """
            INSERT INTO customers (name, email, city, state)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, city, state),
        )
    conn.commit()


def get_seasonal_multiplier(month) -> str:
    """Get seasonal demand multiplier for a given month."""
    # Summer months (Jun, Jul, Aug) = high
    # Winter months (Dec, Jan, Feb) = low
    # Spring/Fall = normal
    summer_months = [6, 7, 8]
    winter_months = [12, 1, 2]

    if month in summer_months:
        return "summer"
    if month in winter_months:
        return "winter"
    return "normal"


def generate_orders(conn, num_orders: Any = 1000) -> None:
    """Generate realistic orders with seasonality."""
    cursor = conn.cursor()

    # Get data
    cursor.execute("SELECT customer_id FROM customers")
    customer_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("""
        SELECT p.product_id, p.price, c.name
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
    """)
    products = [(pid, price, cat) for pid, price, cat in cursor.fetchall()]

    # Generate orders over 24 months
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2024, 12, 31)

    orders_created = 0

    for _ in range(num_orders):
        # Random date in range
        days_diff = (end_date - start_date).days
        # S311: Using random for test data generation (not security-sensitive)
        random_days = random.randint(0, days_diff)
        order_date = start_date + timedelta(days=random_days)

        # Seasonal adjustment
        season = get_seasonal_multiplier(order_date.month)

        # Random customer
        # S311: Using random for test data generation (not security-sensitive)
        customer_id = random.choice(customer_ids)

        # Determine number of items (1-4 items per order, weighted toward 1-2)
        # S311: Using random for test data generation (not security-sensitive)
        num_items = random.choices([1, 2, 3, 4], weights=[40, 35, 20, 5])[0]

        # Select products (with seasonal bias)
        order_products = []
        for _ in range(num_items):
            # Filter products by seasonal demand
            weighted_products = []
            weights = []

            for pid, price, cat in products:
                cat_info = CATEGORIES[cat]

                # Base weight
                weight = cat_info["base_demand"]

                # Seasonal adjustment
                if season == "summer":
                    weight *= cat_info["summer_boost"]
                elif season == "winter":
                    weight *= cat_info["winter_drop"]

                weighted_products.append((pid, price))
                weights.append(weight)

            # Select product
            # S311: Using random for test data generation (not security-sensitive)
            selected = random.choices(weighted_products, weights=weights)[0]
            # S311: Using random for test data generation (not security-sensitive)
            quantity = random.choices([1, 2], weights=[85, 15])[0]  # Mostly single items
            order_products.append((selected[0], selected[1], quantity))

        # Calculate order totals
        subtotal = sum(price * qty for _, price, qty in order_products)
        tax = subtotal * 0.08  # 8% tax
        shipping = 0 if subtotal > 75 else 7.99  # noqa: PLR2004
        total = subtotal + tax + shipping

        # Insert order
        cursor.execute(
            """
            INSERT INTO orders (customer_id, order_date, subtotal, tax, shipping, total, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (customer_id, order_date, subtotal, tax, shipping, total, "completed"),
        )
        order_id = cursor.lastrowid

        # Insert order items
        for product_id, unit_price, quantity in order_products:
            line_total = unit_price * quantity
            cursor.execute(
                """
                INSERT INTO order_items (order_id, product_id, quantity, unit_price, line_total)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, product_id, quantity, unit_price, line_total),
            )

        orders_created += 1

        # Commit in batches
        if orders_created % 100 == 0:
            conn.commit()

    conn.commit()


def print_summary(conn) -> None:
    """Print summary statistics."""
    cursor = conn.cursor()

    # Total orders and revenue
    cursor.execute("SELECT COUNT(*), SUM(total) FROM orders")
    _order_count, _total_revenue = cursor.fetchone()

    # Revenue by category
    cursor.execute("""
        SELECT c.name, SUM(oi.line_total) as revenue, COUNT(DISTINCT o.order_id) as orders
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        GROUP BY c.name
        ORDER BY revenue DESC
    """)
    for _cat, _rev, _orders in cursor.fetchall():
        pass

    # Orders by month (last 6 months of data)
    cursor.execute("""
        SELECT strftime('%Y-%m', order_date) as month,
               COUNT(*) as orders,
               SUM(total) as revenue
        FROM orders
        WHERE order_date >= '2024-01-01'
        GROUP BY month
        ORDER BY month
    """)
    for _month, _orders, _revenue in cursor.fetchall():
        pass


def main() -> None:
    """Main execution."""

    # Remove existing database
    if DB_PATH.exists():
        DB_PATH.unlink()

    # Create and populate database
    conn = sqlite3.connect(DB_PATH)

    try:
        create_schema(conn)
        insert_categories(conn)
        insert_products(conn)
        insert_customers(conn)
        generate_orders(conn, num_orders=1000)
        print_summary(conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
