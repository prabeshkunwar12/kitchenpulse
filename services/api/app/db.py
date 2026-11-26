import os
from collections.abc import Iterator

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


def database_url() -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )


engine = create_engine(database_url(), pool_pre_ping=True, connect_args={"connect_timeout": 5})


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
