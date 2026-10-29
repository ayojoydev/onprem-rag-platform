import sqlite3


def seed_demo(db: sqlite3.Connection) -> None:
    """Fixed fixtures. Money is stored in integer kopecks."""
    db.executemany(
        "INSERT INTO stores (id, name, address) VALUES (?, ?, ?)",
        [
            ("store-1", "Демо: Центральный", "Учебный город, Примерная улица, 1"),
            ("store-2", "Демо: Северный", "Учебный город, Примерная улица, 2"),
            ("store-3", "Демо: Южный", "Учебный город, Примерная улица, 3"),
        ],
    )
    db.executemany(
        "INSERT INTO suppliers (id, name, contact) VALUES (?, ?, ?)",
        [
            ("supplier-1", "Демо: Канцтовары", "office@supplier-one.example"),
            ("supplier-2", "Демо: Бумага", "paper@supplier-two.example"),
            ("supplier-3", "Демо: Электроника", "devices@supplier-three.example"),
        ],
    )
    db.executemany(
        "INSERT INTO products (id, sku, name, price_kopecks, unit) VALUES (?, ?, ?, ?, ?)",
        [
            ("product-1", "SKU-001", "Бумага А4, 500 листов", 39990, "упак."),
            ("product-2", "SKU-002", "Ручка синяя", 5990, "шт."),
            ("product-3", "SKU-003", "Блокнот А5", 14950, "шт."),
            ("product-4", "SKU-004", "Папка для документов", 8990, "шт."),
            ("product-5", "SKU-005", "Клавиатура", 179900, "шт."),
            ("product-6", "SKU-006", "Мышь USB", 79900, "шт."),
        ],
    )
    db.executemany(
        "INSERT INTO product_suppliers (product_id, supplier_id) VALUES (?, ?)",
        [
            ("product-1", "supplier-1"), ("product-1", "supplier-2"),
            ("product-2", "supplier-1"), ("product-3", "supplier-1"),
            ("product-4", "supplier-1"), ("product-5", "supplier-3"),
            ("product-6", "supplier-3"),
        ],
    )
    quantities = {
        "store-1": [25, 100, 30, 15, 4, 8],
        "store-2": [10, 50, 0, 20, 2, 5],
        "store-3": [12, 60, 18, 0, 3, 7],
    }
    db.executemany(
        "INSERT INTO inventory (id, product_id, store_id, quantity) VALUES (?, ?, ?, ?)",
        [
            (f"inventory-{store_number}-{number}", f"product-{number}", store_id, quantity)
            for store_number, (store_id, values) in enumerate(quantities.items(), 1)
            for number, quantity in enumerate(values, 1)
        ],
    )
    db.executemany(
        """INSERT INTO sales
           (id, product_id, store_id, kind, quantity, unit_price_kopecks, occurred_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            # September: store-3 gross 2654.20, returns 59.90, net 2594.30.
            ("sale-1", "product-1", "store-3", "sale", 2, 39990, "2026-09-02T09:00:00+00:00"),
            ("sale-2", "product-2", "store-3", "sale", 5, 5990, "2026-09-10T09:00:00+00:00"),
            ("sale-3", "product-2", "store-3", "return", 1, 5990, "2026-09-11T09:00:00+00:00"),
            ("sale-4", "product-3", "store-3", "sale", 10, 14950, "2026-09-20T09:00:00+00:00"),
            # Boundaries are interpreted in Europe/Moscow, UTC+03:00.
            ("sale-5", "product-2", "store-3", "sale", 1, 5990, "2026-09-30T20:59:59+00:00"),
            ("sale-6", "product-5", "store-3", "sale", 1, 179900, "2026-09-30T21:00:00+00:00"),
            ("sale-7", "product-6", "store-3", "sale", 1, 79900, "2026-08-31T20:59:59+00:00"),
            ("sale-8", "product-2", "store-1", "sale", 3, 5990, "2026-09-10T09:00:00+00:00"),
            ("sale-9", "product-6", "store-2", "sale", 2, 79900, "2026-09-15T09:00:00+00:00"),
        ],
    )
