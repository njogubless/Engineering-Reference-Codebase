"""Async SQLAlchemy: one engine per process, one session per request.

The engine and session factory are created in the app's lifespan (see
app/main.py) and closed on shutdown. Endpoints receive a session through
`SessionDep`; services commit explicitly, so the transaction boundary is
visible in the code that owns the use case.
"""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Any, ClassVar

from fastapi import Depends, Request
from sqlalchemy import DateTime, MetaData
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Deterministic constraint names: Alembic can then alter/drop them reliably.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # SQLAlchemy maps `datetime` to TIMESTAMP WITHOUT TIME ZONE by default.
    # Naive timestamps are ambiguous across DST and servers; store instants
    # as timestamptz (UTC) everywhere. See docs/patterns/41-money-time.
    type_annotation_map: ClassVar[dict[Any, Any]] = {datetime: DateTime(timezone=True)}


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
