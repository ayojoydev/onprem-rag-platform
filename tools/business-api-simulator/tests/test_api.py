from decimal import Decimal
import sqlite3

import pytest
from fastapi.testclient import TestClient

from business_api_simulator.app import create_app

BASE = "/api/v1"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "retail.sqlite3")) as api:
        yield api


def new_product(client, **overrides):
    body = {"sku": "NEW-001", "name": "Тестовый товар", "price": "19.90", "supplier_ids": ["supplier-1"]}
    body.update(overrides)
    response = client.post(f"{BASE}/products", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def report(client, **overrides):
    params = {"store_id": "store-3", "date_from": "2026-09-01", "date_to_exclusive": "2026-10-01"}
    params.update(overrides)
    return client.get(f"{BASE}/business/sales-report", params=params)


def test_seed_counts_openapi_and_health(client):
    assert client.get("/health").json()["status"] == "ok"
    for resource, count in [("products", 6), ("stores", 3), ("suppliers", 3), ("inventory", 18)]:
        response = client.get(f"{BASE}/{resource}")
        assert response.status_code == 200
        assert response.json()["total"] == count
    schema = client.get("/openapi.json").json()
    operations = {operation.get("operationId") for path in schema["paths"].values() for operation in path.values()}
    assert {"get_stock", "get_suppliers", "get_sales_report"} <= operations
    assert client.get("/docs").status_code == 200


def test_product_crud_and_supplier_links(client):
    product = new_product(client, sku="new-001")
    assert product["sku"] == "NEW-001"
    assert product["price"] == "19.90"
    assert product["currency"] == "RUB"
    product_id = product["id"]
    assert client.get(f"{BASE}/products/{product_id}").json() == product
    response = client.patch(f"{BASE}/products/{product_id}", json={"price": "0.10", "supplier_ids": ["supplier-2"]})
    assert response.status_code == 200
    assert response.json()["price"] == "0.10"
    suppliers = client.get(f"{BASE}/business/suppliers", params={"product_id": product_id}).json()["data"]["suppliers"]
    assert [supplier["id"] for supplier in suppliers] == ["supplier-2"]
    assert client.delete(f"{BASE}/products/{product_id}").status_code == 204
    assert client.get(f"{BASE}/products/{product_id}").status_code == 404


@pytest.mark.parametrize("resource,body,patch", [
    ("stores", {"name": "Новый магазин", "address": "Демо, 10"}, {"address": "Демо, 11"}),
    ("suppliers", {"name": "Новый поставщик", "contact": "demo@new.example"}, {"contact": "other@new.example"}),
])
def test_directory_crud(client, resource, body, patch):
    response = client.post(f"{BASE}/{resource}", json=body)
    assert response.status_code == 201
    entity_id = response.json()["id"]
    assert client.get(f"{BASE}/{resource}/{entity_id}").json() == response.json()
    changed = client.patch(f"{BASE}/{resource}/{entity_id}", json=patch)
    assert changed.status_code == 200
    for field, value in patch.items():
        assert changed.json()[field] == value
    assert client.delete(f"{BASE}/{resource}/{entity_id}").status_code == 204
    assert client.get(f"{BASE}/{resource}/{entity_id}").status_code == 404


def test_inventory_crud_is_reflected_in_business_stock(client):
    product = new_product(client)
    response = client.post(f"{BASE}/inventory", json={"product_id": product["id"], "store_id": "store-3", "quantity": 7})
    assert response.status_code == 201
    record = response.json()
    assert client.get(f"{BASE}/inventory/{record['id']}").json() == record
    assert client.patch(f"{BASE}/inventory/{record['id']}", json={"quantity": 0}).status_code == 200
    params = {"sku": product["sku"], "store_id": "store-3"}
    stock = client.get(f"{BASE}/business/stock", params=params)
    assert stock.status_code == 200
    assert stock.json()["data"]["quantity"] == 0
    assert stock.json()["source_id"] == "retail_api"
    assert stock.json()["fetched_at"]
    assert client.delete(f"{BASE}/inventory/{record['id']}").status_code == 204
    # Missing inventory is not a fabricated zero.
    assert client.get(f"{BASE}/business/stock", params=params).status_code == 404


def test_duplicates_return_conflict(client):
    response = client.post(f"{BASE}/products", json={"sku": "sku-001", "name": "Дубль", "price": "1.00"})
    assert response.status_code == 409
    response = client.post(f"{BASE}/inventory", json={"product_id": "product-1", "store_id": "store-3", "quantity": 5})
    assert response.status_code == 409


@pytest.mark.parametrize("price", ["-0.01", "1.001", "NaN", "1000000000.00"])
def test_invalid_money_is_rejected(client, price):
    response = client.post(f"{BASE}/products", json={"sku": "BAD-PRICE", "name": "Товар", "price": price})
    assert response.status_code == 422


@pytest.mark.parametrize("quantity", [-1, 1.5, True, "2", 1_000_001])
def test_invalid_quantity_is_rejected(client, quantity):
    response = client.patch(f"{BASE}/inventory/inventory-3-1", json={"quantity": quantity})
    assert response.status_code == 422
    assert client.get(f"{BASE}/inventory/inventory-3-1").json()["quantity"] == 12


@pytest.mark.parametrize("body", [{}, {"name": None}, {"id": "product-hijacked"}, {"name": "   "}])
def test_invalid_patch_does_not_modify_product(client, body):
    before = client.get(f"{BASE}/products/product-1").json()
    assert client.patch(f"{BASE}/products/product-1", json=body).status_code == 422
    assert client.get(f"{BASE}/products/product-1").json() == before


def test_failed_supplier_link_rolls_back_the_whole_product_change(client):
    before = client.get(f"{BASE}/products/product-1").json()
    response = client.patch(f"{BASE}/products/product-1", json={"price": "1.00", "supplier_ids": ["missing"]})
    assert response.status_code == 404
    assert client.get(f"{BASE}/products/product-1").json() == before
    count = client.get(f"{BASE}/products").json()["total"]
    response = client.post(f"{BASE}/products", json={"sku": "ROLLBACK", "name": "Не сохранится", "price": "1.00", "supplier_ids": ["missing"]})
    assert response.status_code == 404
    assert client.get(f"{BASE}/products").json()["total"] == count


def test_referenced_products_and_stores_cannot_be_deleted(client):
    assert client.delete(f"{BASE}/products/product-1").status_code == 409
    assert client.delete(f"{BASE}/stores/store-3").status_code == 409
    assert client.get(f"{BASE}/products/product-1").status_code == 200
    assert client.get(f"{BASE}/stores/store-3").status_code == 200


def test_supplier_delete_removes_link_and_empty_list_can_detach(client):
    assert client.delete(f"{BASE}/suppliers/supplier-2").status_code == 204
    product = client.get(f"{BASE}/products/product-1").json()
    assert product["supplier_ids"] == ["supplier-1"]
    response = client.patch(f"{BASE}/products/product-1", json={"supplier_ids": []})
    assert response.status_code == 200
    assert response.json()["supplier_ids"] == []


def test_inventory_references_must_exist(client):
    response = client.post(f"{BASE}/inventory", json={"product_id": "missing", "store_id": "store-3", "quantity": 1})
    assert response.status_code == 404
    assert client.get(f"{BASE}/inventory").json()["total"] == 18


def test_search_handles_russian_case_and_literal_sql(client):
    search = client.get(f"{BASE}/products", params={"q": "БУМАГА"}).json()
    assert [item["sku"] for item in search["items"]] == ["SKU-001"]
    assert client.get(f"{BASE}/products", params={"q": "%' OR 1=1--"}).json()["total"] == 0
    assert client.get(f"{BASE}/products", params={"limit": 2, "offset": 2}).json()["total"] == 6
    assert len(client.get(f"{BASE}/products", params={"limit": 2, "offset": 2}).json()["items"]) == 2
    assert client.get(f"{BASE}/products", params={"limit": 201}).status_code == 422


def test_sales_report_uses_exact_money_store_scope_and_moscow_boundaries(client):
    response = report(client)
    assert response.status_code == 200
    data = response.json()["data"]
    # Independent expected sums: 2*399.90 + 5*59.90 + 10*149.50 + 59.90.
    assert data["gross_revenue"] == "2654.20"
    assert data["returns"] == "59.90"
    assert data["net_revenue"] == "2594.30"
    assert data["sales_quantity"] == 18
    assert data["returns_quantity"] == 1
    assert data["records_count"] == 5
    assert data["timezone"] == "Europe/Moscow"
    october = report(client, date_from="2026-10-01", date_to_exclusive="2026-10-02").json()["data"]
    assert october["gross_revenue"] == "1799.00"
    assert october["records_count"] == 1


def test_repricing_products_does_not_change_historical_report(client):
    assert client.patch(f"{BASE}/products/product-1", json={"price": "0.01"}).status_code == 200
    assert report(client).json()["data"]["gross_revenue"] == "2654.20"


def test_report_uses_historical_timezone_rules_instead_of_fixed_offset(client):
    # Moscow used UTC+04:00 in September 2012. The second sale belongs to October.
    with sqlite3.connect(client.app.state.database_path) as db:
        db.executemany(
            "INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("historic-1", "product-1", "store-3", "sale", 1, 990, "2012-09-30T19:59:59+00:00"),
                ("historic-2", "product-1", "store-3", "sale", 1, 1990, "2012-09-30T20:00:00+00:00"),
            ],
        )
    data = report(client, date_from="2012-09-01", date_to_exclusive="2012-10-01").json()["data"]
    assert data["gross_revenue"] == "9.90"
    assert data["records_count"] == 1


@pytest.mark.parametrize("params", [
    {"date_from": "2026-10-01"}, {"date_from": "2026-10-02"},
    {"date_from": "2020-01-01"}, {"date_from": "0001-01-01"},
    {"date_to_exclusive": "not-a-date"},
])
def test_invalid_report_period_is_rejected(client, params):
    assert report(client, **params).status_code == 422


def test_empty_report_and_missing_business_entities_are_distinct(client):
    empty = report(client, date_from="2027-01-01", date_to_exclusive="2027-02-01").json()["data"]
    assert Decimal(empty["net_revenue"]) == 0
    assert empty["records_count"] == 0
    assert report(client, store_id="missing").status_code == 404
    assert client.get(f"{BASE}/business/suppliers", params={"product_id": "missing"}).status_code == 404
    assert client.get(f"{BASE}/business/stock", params={"sku": "missing", "store_id": "store-3"}).status_code == 404


def test_restart_preserves_changes_without_reseeding(tmp_path):
    path = tmp_path / "persistent.sqlite3"
    with TestClient(create_app(path)) as first:
        product = new_product(first)
        assert first.patch(f"{BASE}/inventory/inventory-3-1", json={"quantity": 99}).status_code == 200
        assert first.delete(f"{BASE}/suppliers/supplier-2").status_code == 204
    with TestClient(create_app(path)) as second:
        assert second.get(f"{BASE}/products/{product['id']}").status_code == 200
        assert second.get(f"{BASE}/products").json()["total"] == 7
        assert second.get(f"{BASE}/inventory/inventory-3-1").json()["quantity"] == 99
        assert second.get(f"{BASE}/suppliers/supplier-2").status_code == 404


def test_initially_empty_database_is_not_silently_populated_on_restart(tmp_path):
    path = tmp_path / "empty.sqlite3"
    with TestClient(create_app(path, seed_demo=False)) as first:
        assert first.get(f"{BASE}/products").json()["total"] == 0
    with TestClient(create_app(path, seed_demo=True)) as second:
        assert second.get(f"{BASE}/products").json()["total"] == 0
