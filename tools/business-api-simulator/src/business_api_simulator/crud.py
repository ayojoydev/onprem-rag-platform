from fastapi import APIRouter, Response

from . import repository as repo
from .dependencies import Database, Limit, Offset
from .models import (
    Inventory, InventoryCreate, InventoryPatch, Page, Product, ProductCreate,
    ProductPatch, Store, StoreCreate, StorePatch, Supplier, SupplierCreate, SupplierPatch,
)

router = APIRouter(prefix="/api/v1")


@router.get("/products", response_model=Page[Product], tags=["Товары"])
def list_products(db: Database, q: str | None = None, limit: Limit = 50, offset: Offset = 0):
    return repo.page(db, "products", limit, offset, search=q)


@router.post("/products", response_model=Product, status_code=201, tags=["Товары"])
def create_product(body: ProductCreate, db: Database):
    values = body.model_dump(exclude={"supplier_ids", "price"})
    values["price_kopecks"] = int(body.price * 100)
    with db:
        entity_id = repo.insert(db, "products", values, "product")
        repo.replace_suppliers(db, entity_id, body.supplier_ids)
    return repo.product_view(db, repo.require(db, "products", entity_id))


@router.get("/products/{entity_id}", response_model=Product, tags=["Товары"])
def get_product(entity_id: str, db: Database):
    return repo.product_view(db, repo.require(db, "products", entity_id))


@router.patch("/products/{entity_id}", response_model=Product, tags=["Товары"])
def patch_product(entity_id: str, body: ProductPatch, db: Database):
    values = body.model_dump(exclude_unset=True, exclude={"supplier_ids"})
    if "price" in values:
        values["price_kopecks"] = int(values.pop("price") * 100)
    with db:
        repo.require(db, "products", entity_id)
        repo.update(db, "products", entity_id, values)
        if "supplier_ids" in body.model_fields_set:
            repo.replace_suppliers(db, entity_id, body.supplier_ids)
    return repo.product_view(db, repo.require(db, "products", entity_id))


@router.delete("/products/{entity_id}", status_code=204, tags=["Товары"])
def delete_product(entity_id: str, db: Database):
    with db:
        repo.delete(db, "products", entity_id)
    return Response(status_code=204)


@router.get("/stores", response_model=Page[Store], tags=["Магазины"])
def list_stores(db: Database, limit: Limit = 50, offset: Offset = 0):
    return repo.page(db, "stores", limit, offset)


@router.post("/stores", response_model=Store, status_code=201, tags=["Магазины"])
def create_store(body: StoreCreate, db: Database):
    with db:
        entity_id = repo.insert(db, "stores", body.model_dump(), "store")
    return repo.require(db, "stores", entity_id)


@router.get("/stores/{entity_id}", response_model=Store, tags=["Магазины"])
def get_store(entity_id: str, db: Database):
    return repo.require(db, "stores", entity_id)


@router.patch("/stores/{entity_id}", response_model=Store, tags=["Магазины"])
def patch_store(entity_id: str, body: StorePatch, db: Database):
    with db:
        repo.require(db, "stores", entity_id)
        repo.update(db, "stores", entity_id, body.model_dump(exclude_unset=True))
    return repo.require(db, "stores", entity_id)


@router.delete("/stores/{entity_id}", status_code=204, tags=["Магазины"])
def delete_store(entity_id: str, db: Database):
    with db:
        repo.delete(db, "stores", entity_id)
    return Response(status_code=204)


@router.get("/suppliers", response_model=Page[Supplier], tags=["Поставщики"])
def list_suppliers(db: Database, limit: Limit = 50, offset: Offset = 0):
    return repo.page(db, "suppliers", limit, offset)


@router.post("/suppliers", response_model=Supplier, status_code=201, tags=["Поставщики"])
def create_supplier(body: SupplierCreate, db: Database):
    with db:
        entity_id = repo.insert(db, "suppliers", body.model_dump(), "supplier")
    return repo.require(db, "suppliers", entity_id)


@router.get("/suppliers/{entity_id}", response_model=Supplier, tags=["Поставщики"])
def get_supplier(entity_id: str, db: Database):
    return repo.require(db, "suppliers", entity_id)


@router.patch("/suppliers/{entity_id}", response_model=Supplier, tags=["Поставщики"])
def patch_supplier(entity_id: str, body: SupplierPatch, db: Database):
    with db:
        repo.require(db, "suppliers", entity_id)
        repo.update(db, "suppliers", entity_id, body.model_dump(exclude_unset=True))
    return repo.require(db, "suppliers", entity_id)


@router.delete("/suppliers/{entity_id}", status_code=204, tags=["Поставщики"])
def delete_supplier(entity_id: str, db: Database):
    with db:
        repo.delete(db, "suppliers", entity_id)
    return Response(status_code=204)


@router.get("/inventory", response_model=Page[Inventory], tags=["Остатки"])
def list_inventory(
    db: Database, store_id: str | None = None, product_id: str | None = None,
    limit: Limit = 50, offset: Offset = 0,
):
    return repo.page(db, "inventory", limit, offset, filters={"store_id": store_id, "product_id": product_id})


@router.post("/inventory", response_model=Inventory, status_code=201, tags=["Остатки"])
def create_inventory(body: InventoryCreate, db: Database):
    with db:
        repo.require(db, "products", body.product_id)
        repo.require(db, "stores", body.store_id)
        entity_id = repo.insert(db, "inventory", body.model_dump(), "inventory")
    return repo.require(db, "inventory", entity_id)


@router.get("/inventory/{entity_id}", response_model=Inventory, tags=["Остатки"])
def get_inventory(entity_id: str, db: Database):
    return repo.require(db, "inventory", entity_id)


@router.patch("/inventory/{entity_id}", response_model=Inventory, tags=["Остатки"])
def patch_inventory(entity_id: str, body: InventoryPatch, db: Database):
    with db:
        repo.require(db, "inventory", entity_id)
        repo.update(db, "inventory", entity_id, body.model_dump(exclude_unset=True))
    return repo.require(db, "inventory", entity_id)


@router.delete("/inventory/{entity_id}", status_code=204, tags=["Остатки"])
def delete_inventory(entity_id: str, db: Database):
    with db:
        repo.delete(db, "inventory", entity_id)
    return Response(status_code=204)
