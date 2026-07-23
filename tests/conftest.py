import os
import sys
import pytest

# Make the `agent` package importable (repo-root/agent/agent/...).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from fastapi.testclient import TestClient  # noqa: E402
from webhook import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)
