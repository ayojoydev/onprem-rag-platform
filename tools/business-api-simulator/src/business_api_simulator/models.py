from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Name = Annotated[str, Field(min_length=1, max_length=200)]
Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]
Sku = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")]
Money = Annotated[Decimal, Field(ge=0, max_digits=11, decimal_places=2)]
Quantity = Annotated[int, Field(strict=True, ge=0, le=1_000_000)]
T = TypeVar("T")


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Patch(Model):
    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("Укажите хотя бы одно изменяемое поле")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Изменяемые поля не могут быть null")
        return self


class ProductCreate(Model):
    sku: Sku
    name: Name
    price: Money
    unit: Literal["шт.", "упак."] = "шт."
    supplier_ids: list[Identifier] = Field(default_factory=list, max_length=100)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.upper()

    @field_validator("supplier_ids")
    @classmethod
    def unique_suppliers(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Поставщики не должны повторяться")
        return value


class ProductPatch(Patch):
    sku: Sku | None = None
    name: Name | None = None
    price: Money | None = None
    unit: Literal["шт.", "упак."] | None = None
    supplier_ids: list[Identifier] | None = Field(default=None, max_length=100)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("supplier_ids")
    @classmethod
    def unique_suppliers(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("Поставщики не должны повторяться")
        return value


class Product(ProductCreate):
    id: str
    currency: Literal["RUB"] = "RUB"


class StoreCreate(Model):
    name: Name
    address: Annotated[str, Field(min_length=1, max_length=500)]


class StorePatch(Patch):
    name: Name | None = None
    address: Annotated[str, Field(min_length=1, max_length=500)] | None = None


class Store(StoreCreate):
    id: str


class SupplierCreate(Model):
    name: Name
    contact: Annotated[str, Field(min_length=1, max_length=200)]


class SupplierPatch(Patch):
    name: Name | None = None
    contact: Annotated[str, Field(min_length=1, max_length=200)] | None = None


class Supplier(SupplierCreate):
    id: str


class InventoryCreate(Model):
    product_id: Identifier
    store_id: Identifier
    quantity: Quantity


class InventoryPatch(Patch):
    quantity: Quantity | None = None


class Inventory(InventoryCreate):
    id: str


class Page(Model, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class StockData(Model):
    product_id: str
    sku: str
    product_name: str
    store_id: str
    store_name: str
    quantity: int
    unit: str


class SuppliersData(Model):
    product_id: str
    sku: str
    suppliers: list[Supplier]


class SalesReport(Model):
    store_id: str
    date_from: date
    date_to_exclusive: date
    timezone: Literal["Europe/Moscow"] = "Europe/Moscow"
    currency: Literal["RUB"] = "RUB"
    gross_revenue: Decimal
    returns: Decimal
    net_revenue: Decimal
    sales_quantity: int
    returns_quantity: int
    records_count: int
    calculation: str


class ToolResult(Model, Generic[T]):
    status: Literal["ok"] = "ok"
    source_id: Literal["retail_api"] = "retail_api"
    fetched_at: datetime
    data: T
