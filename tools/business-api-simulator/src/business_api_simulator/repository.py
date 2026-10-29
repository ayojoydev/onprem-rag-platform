import sqlite3
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

TABLES = {
    "products": {"sku", "name", "price_kopecks", "unit"},
    "stores": {"name", "address"},
    "suppliers": {"name", "contact"},
    "inventory": {"product_id", "store_id", "quantity"},
}


def check_table(table: str, columns=()) -> None:
    if table not in TABLES or not set(columns) <= TABLES[table]:
        raise ValueError("Unknown repository table or columns")


def require(db: sqlite3.Connection, table: str, entity_id: str) -> dict:
    check_table(table)
    row = db.execute(f"SELECT * FROM {table} WHERE id = ?", (entity_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Запись не найдена")
    return dict(row)


def money(kopecks: int) -> Decimal:
    return (Decimal(kopecks) / Decimal(100)).quantize(Decimal("0.01"))


def product_view(db: sqlite3.Connection, row: dict) -> dict:
    result = dict(row)
    result["price"] = money(result.pop("price_kopecks"))
    result["currency"] = "RUB"
    result["supplier_ids"] = [
        supplier[0]
        for supplier in db.execute(
            "SELECT supplier_id FROM product_suppliers WHERE product_id = ? ORDER BY supplier_id",
            (result["id"],),
        )
    ]
    return result


def page(db, table, limit, offset, *, search=None, filters=None) -> dict:
    check_table(table)
    clauses, parameters = [], []
    if search:
        if table != "products":
            raise ValueError("Search is supported only for products")
        clauses.append("(instr(casefold(name), ?) > 0 OR instr(casefold(sku), ?) > 0)")
        parameters.extend([search.strip().casefold()] * 2)
    for column, value in (filters or {}).items():
        check_table(table, [column])
        if value is not None:
            clauses.append(f"{column} = ?")
            parameters.append(value)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = db.execute(f"SELECT COUNT(*) FROM {table}{where}", parameters).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM {table}{where} ORDER BY id LIMIT ? OFFSET ?",
        [*parameters, limit, offset],
    ).fetchall()
    items = [product_view(db, dict(row)) if table == "products" else dict(row) for row in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def insert(db, table: str, values: dict, prefix: str) -> str:
    check_table(table, values)
    entity_id = f"{prefix}-{uuid4().hex}"
    columns = ["id", *values]
    placeholders = ", ".join("?" for _ in columns)
    db.execute(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        [entity_id, *values.values()],
    )
    return entity_id


def update(db, table: str, entity_id: str, values: dict) -> None:
    check_table(table, values)
    if values:
        assignments = ", ".join(f"{column} = ?" for column in values)
        db.execute(f"UPDATE {table} SET {assignments} WHERE id = ?", [*values.values(), entity_id])


def delete(db, table: str, entity_id: str) -> None:
    require(db, table, entity_id)
    db.execute(f"DELETE FROM {table} WHERE id = ?", (entity_id,))


def replace_suppliers(db, product_id: str, supplier_ids: list[str]) -> None:
    for supplier_id in supplier_ids:
        require(db, "suppliers", supplier_id)
    db.execute("DELETE FROM product_suppliers WHERE product_id = ?", (product_id,))
    db.executemany(
        "INSERT INTO product_suppliers (product_id, supplier_id) VALUES (?, ?)",
        [(product_id, supplier_id) for supplier_id in supplier_ids],
    )
