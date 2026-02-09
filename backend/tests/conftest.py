"""Shared fixtures for all test modules."""
import json
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set COMPILED_DIR before any app module import to prevent ConfigGenerator
# from trying to mkdir on read-only system paths.
_test_compiled_dir = tempfile.mkdtemp(prefix="ktizo_test_")
os.environ["COMPILED_DIR"] = _test_compiled_dir

from app.db.database import Base


@pytest.fixture
def db_engine():
    """In-memory SQLite for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Session bound to in-memory engine."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_db(db_session):
    """Patch _db() at the ws_handler module level to return the test session."""
    with patch("app.api.ws_handler._db", return_value=db_session):
        yield db_session


@pytest.fixture
def mock_ws():
    """Fake WebSocket that captures sent messages."""
    ws = AsyncMock()
    ws.sent_messages = []

    async def capture_send_json(msg):
        ws.sent_messages.append(msg)

    ws.send_json = AsyncMock(side_effect=capture_send_json)
    return ws


@pytest.fixture
def mock_broadcast():
    """Patch _broadcast to capture broadcast events."""
    events = []

    async def capture(event_type, data=None):
        events.append({"type": event_type, "data": data})

    with patch("app.api.ws_handler._broadcast", side_effect=capture):
        yield events


@pytest.fixture
def mock_helm_runner():
    """Mock the helm_runner singleton with default success returns."""
    runner = MagicMock()
    runner.repo_add = AsyncMock(return_value=(True, "repo added"))
    runner.repo_update = AsyncMock(return_value=(True, "updated"))
    runner.install = AsyncMock(return_value=(True, "installed"))
    runner.upgrade = AsyncMock(return_value=(True, "upgraded"))
    runner.uninstall = AsyncMock(return_value=(True, "uninstalled"))
    runner.get_status = AsyncMock(return_value={"version": 1, "info": {"app_version": "1.0"}})
    runner.list_releases = AsyncMock(return_value=[])
    runner.search_versions = AsyncMock(return_value=[])
    return runner


@pytest.fixture
def mock_kubectl():
    """Patch _find_kubectl to return a fake path."""
    with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"):
        yield


@pytest.fixture
def mock_subprocess():
    """Patch asyncio.create_subprocess_exec for kubectl/talosctl calls."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(b'{}', b''))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_create:
        yield mock_create, mock_proc


@pytest.fixture
def mock_log_action():
    """Patch log_action to no-op."""
    with patch("app.api.ws_handler.log_action", new_callable=AsyncMock):
        yield


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def seed_helm_release(db_session, **overrides):
    """Create a HelmRelease in the test DB."""
    from app.db.models import HelmRelease
    defaults = {
        "release_name": "test-release",
        "namespace": "default",
        "chart_name": "test/chart",
        "status": "deployed",
    }
    defaults.update(overrides)
    release = HelmRelease(**defaults)
    db_session.add(release)
    db_session.commit()
    db_session.refresh(release)
    return release


def seed_helm_repository(db_session, name="test-repo", url="https://example.com/charts"):
    """Create a HelmRepository in the test DB."""
    from app.db.models import HelmRepository
    repo = HelmRepository(name=name, url=url)
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)
    return repo


def seed_device(db_session, **overrides):
    """Create a Device in the test DB."""
    from app.db.models import Device, DeviceStatus, DeviceRole
    defaults = {
        "mac_address": "AA:BB:CC:DD:EE:01",
        "hostname": "node-01",
        "ip_address": "10.0.128.1",
        "role": DeviceRole.WORKER,
        "status": DeviceStatus.APPROVED,
    }
    defaults.update(overrides)
    device = Device(**defaults)
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device


def get_ws_response(mock_ws, index=-1):
    """Get the response from mock WebSocket. Returns (data, error) tuple."""
    msg = mock_ws.sent_messages[index]
    return msg.get("data"), msg.get("error")
