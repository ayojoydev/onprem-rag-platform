import sqlite3
from typing import Annotated

from fastapi import Depends, Query, Request

from .database import connect


def database(request: Request):
    db = connect(request.app.state.database_path)
    try:
        yield db
    finally:
        db.close()


Database = Annotated[sqlite3.Connection, Depends(database)]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]
