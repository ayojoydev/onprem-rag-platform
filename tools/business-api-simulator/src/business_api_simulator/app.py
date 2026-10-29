import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse

from . import business, crud
from .database import initialize
from .dependencies import Database


def create_app(database_path: str | Path | None = None, seed_demo: bool | None = None) -> FastAPI:
    path = Path(database_path or os.environ.get("SIMULATOR_DATABASE_PATH", "data/business-api.sqlite3")).resolve()
    if seed_demo is None:
        value = os.environ.get("SIMULATOR_SEED_DEMO", "true").lower()
        if value not in ("true", "false", "1", "0"):
            raise ValueError("SIMULATOR_SEED_DEMO must be true, false, 1 or 0")
        seed_demo = value in ("true", "1")

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        initialize(path, seed=seed_demo)
        yield

    application = FastAPI(
        title="Демонстрационный бизнес-API",
        description=(
            "Синтетические товары, магазины, поставщики и остатки для On-Prem RAG Platform. "
            "CRUD — стенд для подготовки данных; /business — будущие инструменты ассистента. "
            "Роли и авторизация Runtime в этом локальном симуляторе не реализованы."
        ),
        version="0.1.0", lifespan=lifespan,
    )
    application.state.database_path = path
    application.include_router(crud.router)
    application.include_router(business.router)

    @application.exception_handler(sqlite3.IntegrityError)
    async def integrity_error(request, exc):
        return JSONResponse(status_code=409, content={
            "detail": "Запись дублирует существующую либо связана с другими данными. Проверьте SKU, пару товар/магазин и ссылки."
        })

    @application.get("/", include_in_schema=False)
    def index():
        return RedirectResponse("/docs")

    @application.get("/health", tags=["Состояние"])
    def health(db: Database):
        db.execute("SELECT 1").fetchone()
        return {"status": "ok", "dataset": "synthetic", "version": "0.1.0"}

    return application


app = create_app()
