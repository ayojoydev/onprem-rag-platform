import sqlite3
from contextlib import closing
from pathlib import Path

from .seed import seed_demo

SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stores (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, address TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS suppliers (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, contact TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    sku TEXT NOT NULL COLLATE NOCASE UNIQUE,
    name TEXT NOT NULL,
    price_kopecks INTEGER NOT NULL CHECK(price_kopecks >= 0),
    unit TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS product_suppliers (
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
    PRIMARY KEY(product_id, supplier_id)
);
CREATE TABLE IF NOT EXISTS inventory (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    store_id TEXT NOT NULL REFERENCES stores(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK(quantity >= 0),
    UNIQUE(product_id, store_id)
);
CREATE TABLE IF NOT EXISTS sales (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    store_id TEXT NOT NULL REFERENCES stores(id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK(kind IN ('sale', 'return')),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price_kopecks INTEGER NOT NULL CHECK(unit_price_kopecks >= 0),
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sales_store_time ON sales(store_id, occurred_at);
"""


def connect(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path, timeout=10, check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.create_function("casefold", 1, str.casefold, deterministic=True)
    return db


def initialize(path: Path, seed: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            raise RuntimeError(f"Unsupported simulator database schema: {version}")
        db.executescript(SCHEMA)
        with db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM metadata WHERE key = 'initialized'").fetchone():
                if seed:
                    seed_demo(db)
                db.execute("INSERT INTO metadata VALUES ('initialized', ?)", ("demo-v1" if seed else "empty",))
            db.execute("PRAGMA user_version = 1")
