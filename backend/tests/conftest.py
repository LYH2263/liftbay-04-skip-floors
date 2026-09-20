import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Point the app at in-memory SQLite before any app module is imported, so the
# module-level engine never binds to the configured Postgres URL (and tests
# need no database server or psycopg2).
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import BlockedFloor, Building, ElevatorCar  # noqa: E402


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def _get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db
    # Constructed without a `with` block so the app lifespan (which connects to
    # the configured real engine and seeds) does not run; the db_session fixture
    # creates the schema on in-memory SQLite instead.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def building(db_session):
    b = Building(name="测试楼", floors=18)
    db_session.add(b)
    db_session.flush()
    return b


@pytest.fixture()
def cars(db_session, building):
    rows = [
        ElevatorCar(building_id=building.id, label="T1", floor=1, direction="idle", load=0, capacity=10),
        ElevatorCar(building_id=building.id, label="T2", floor=10, direction="up", load=9, capacity=10),
    ]
    db_session.add_all(rows)
    db_session.flush()
    return rows


@pytest.fixture()
def blocked_13(db_session, building):
    row = BlockedFloor(building_id=building.id, floor=13)
    db_session.add(row)
    db_session.flush()
    return row
