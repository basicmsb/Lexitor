import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)
