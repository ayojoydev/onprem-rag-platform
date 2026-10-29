from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException

from . import repository as repo
from .dependencies import Database
from .models import SalesReport, StockData, SuppliersData, ToolResult

router = APIRouter(prefix="/api/v1/business", tags=["Бизнес-операции"])
MOSCOW = ZoneInfo("Europe/Moscow")


def result(data: dict) -> dict:
    return {"status": "ok", "source_id": "retail_api", "fetched_at": datetime.now(timezone.utc), "data": data}


@router.get("/stock", response_model=ToolResult[StockData], operation_id="get_stock")
def get_stock(sku: str, store_id: str, db: Database):
    store = repo.require(db, "stores", store_id)
    product = db.execute("SELECT * FROM products WHERE sku = ?", (sku.strip(),)).fetchone()
    if product is None:
        raise HTTPException(404, "Товар с таким артикулом не найден")
    inventory = db.execute(
        "SELECT quantity FROM inventory WHERE product_id = ? AND store_id = ?", (product["id"], store_id)
    ).fetchone()
    if inventory is None:
        raise HTTPException(404, "Для товара и магазина запись об остатке не заведена")
    return result({
        "product_id": product["id"], "sku": product["sku"], "product_name": product["name"],
        "store_id": store_id, "store_name": store["name"], "quantity": inventory["quantity"], "unit": product["unit"],
    })


@router.get("/suppliers", response_model=ToolResult[SuppliersData], operation_id="get_suppliers")
def get_suppliers(product_id: str, db: Database):
    product = repo.require(db, "products", product_id)
    suppliers = db.execute(
        """SELECT s.* FROM suppliers s
           JOIN product_suppliers ps ON ps.supplier_id = s.id
           WHERE ps.product_id = ? ORDER BY s.id""", (product_id,)
    ).fetchall()
    return result({"product_id": product_id, "sku": product["sku"], "suppliers": [dict(row) for row in suppliers]})


@router.get("/sales-report", response_model=ToolResult[SalesReport], operation_id="get_sales_report")
def get_sales_report(store_id: str, date_from: date, date_to_exclusive: date, db: Database):
    repo.require(db, "stores", store_id)
    if date_from < date(1970, 1, 1) or date_to_exclusive > date(2101, 1, 1):
        raise HTTPException(422, "Поддерживаются периоды с 1970 по 2100 год")
    days = (date_to_exclusive - date_from).days
    if not 1 <= days <= 366:
        raise HTTPException(422, "Период должен быть от 1 до 366 дней; верхняя граница не включается")
    start = datetime.combine(date_from, time.min, MOSCOW).astimezone(timezone.utc).isoformat()
    end = datetime.combine(date_to_exclusive, time.min, MOSCOW).astimezone(timezone.utc).isoformat()
    rows = db.execute(
        """SELECT kind, quantity, unit_price_kopecks FROM sales
           WHERE store_id = ? AND occurred_at >= ? AND occurred_at < ?""", (store_id, start, end)
    ).fetchall()
    gross = sum(row["quantity"] * row["unit_price_kopecks"] for row in rows if row["kind"] == "sale")
    returns = sum(row["quantity"] * row["unit_price_kopecks"] for row in rows if row["kind"] == "return")
    return result({
        "store_id": store_id, "date_from": date_from, "date_to_exclusive": date_to_exclusive,
        "gross_revenue": repo.money(gross), "returns": repo.money(returns), "net_revenue": repo.money(gross - returns),
        "sales_quantity": sum(row["quantity"] for row in rows if row["kind"] == "sale"),
        "returns_quantity": sum(row["quantity"] for row in rows if row["kind"] == "return"),
        "records_count": len(rows),
        "calculation": "Выручка = сумма продаж; чистая выручка = продажи минус возвраты. Налоги и себестоимость не моделируются.",
    })
