import os
from unittest.mock import MagicMock, patch

import pytest

# Must be set before app.config is imported — load_dotenv() won't override existing vars
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-anon-key")
os.environ.setdefault("GOOGLE_CREDENTIALS_PATH", "/fake/creds.json")

# Prevent real Supabase client construction when app.config is imported at collection time
_patcher = patch("supabase.create_client", return_value=MagicMock())
_patcher.start()

from fastapi.testclient import TestClient  # noqa: E402

from app import config  # noqa: E402
from app.auth import verify_user  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_supabase():
    """Replace config.supabase with a fresh MagicMock for each test."""
    mock = MagicMock()
    config.supabase = mock
    return mock


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.email = "allowed@example.com"
    return user


@pytest.fixture
def auth_client(mock_user):
    """TestClient with verify_user dependency bypassed."""
    app.dependency_overrides[verify_user] = lambda: mock_user
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def drive_service_mock(files: list) -> MagicMock:
    svc = MagicMock()
    svc.files.return_value.list.return_value.execute.return_value = {"files": files}
    return svc
