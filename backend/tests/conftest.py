import os

os.environ["DATABASE_URL"] = "sqlite:///./test_epr_portal.db"
os.environ["JWT_SECRET"] = "test-secret"

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)

