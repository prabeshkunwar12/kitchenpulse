import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

if os.environ.get("POSTGRES_DB") != "kitchenpulse_test":
    raise RuntimeError("Run tests only against the isolated kitchenpulse_test database.")

from app.db import engine
from app.inventory.models import Category
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def migrate():
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT current_database()")) == "kitchenpulse_test"
    command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")


@pytest.fixture(autouse=True)
def clean_inventory():
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE stock_transactions, items, categories RESTART IDENTITY"))


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def category():
    with Session(engine) as session, session.begin():
        entry = Category(name="Test Seafood")
        session.add(entry)
        session.flush()
        return entry.id
