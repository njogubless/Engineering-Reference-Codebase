"""Create the configured database if it does not exist (local dev and tests).

Production databases are provisioned by infrastructure, never by the app.
Usage: FASTAPI_ENV_FILE=.env.test python -m scripts.ensure_database
"""

import asyncio
from urllib.parse import urlsplit

import asyncpg

from app.core.config import get_settings


async def ensure_database() -> None:
    url = urlsplit(str(get_settings().database_url))
    name = url.path.lstrip("/")
    admin_dsn = url._replace(scheme="postgresql", path="/postgres").geturl()
    connection = await asyncpg.connect(admin_dsn)
    try:
        exists = await connection.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name)
        if not exists:
            # Identifiers cannot be bound as parameters; quote it safely instead.
            quoted = '"' + name.replace('"', '""') + '"'
            await connection.execute(f"CREATE DATABASE {quoted}")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(ensure_database())
