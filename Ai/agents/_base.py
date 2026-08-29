import os

from agno.db.base import BaseDb
from agno.db.postgres import PostgresDb


def resolve_db(db: BaseDb | None) -> BaseDb:
    """Retorna o db passado ou cria um PostgresDb a partir de DATABASE_URL."""
    if db is not None:
        return db

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "Variável de ambiente DATABASE_URL não encontrada. "
            "Configure-a no .env antes de iniciar o agente."
        )

    sync_url = database_url.replace("+psycopg_async", "+psycopg").replace(
        "+asyncpg", "+psycopg"
    )
    return PostgresDb(db_url=sync_url)
