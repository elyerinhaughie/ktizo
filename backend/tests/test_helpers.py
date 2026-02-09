"""Tests for helper functions in app.api.ws_handler."""
import json
import enum
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.api.ws_handler import _serialize, _respond, _save_disk_partition, _remove_disk_partition, _disk_name_from_path


# ---------------------------------------------------------------------------
# _serialize
# ---------------------------------------------------------------------------

class TestSerialize:
    """Unit tests for the _serialize helper."""

    def test_none(self):
        assert _serialize(None) is None

    def test_primitive_string(self):
        assert _serialize("hello") == "hello"

    def test_primitive_int(self):
        assert _serialize(42) == 42

    def test_primitive_float(self):
        assert _serialize(3.14) == 3.14

    def test_primitive_bool(self):
        assert _serialize(True) is True

    def test_empty_list(self):
        assert _serialize([]) == []

    def test_list_of_primitives(self):
        assert _serialize([1, "two", None]) == [1, "two", None]

    def test_nested_list(self):
        assert _serialize([[1, 2], [3]]) == [[1, 2], [3]]

    def test_empty_dict(self):
        assert _serialize({}) == {}

    def test_dict_of_primitives(self):
        result = _serialize({"a": 1, "b": "two"})
        assert result == {"a": 1, "b": "two"}

    def test_dict_with_none_value(self):
        result = _serialize({"key": None})
        assert result == {"key": None}

    def test_nested_dict(self):
        result = _serialize({"outer": {"inner": 42}})
        assert result == {"outer": {"inner": 42}}

    def test_pydantic_model(self):
        """Objects with model_dump() are treated as Pydantic models."""
        mock_pydantic = MagicMock()
        mock_pydantic.model_dump.return_value = {"field": "value"}
        # Ensure it does not have __table__ (SQLAlchemy check comes after)
        del mock_pydantic.__table__
        result = _serialize(mock_pydantic)
        assert result == {"field": "value"}
        mock_pydantic.model_dump.assert_called_once()

    def test_sqlalchemy_model_basic(self):
        """Objects with __table__ are treated as SQLAlchemy models."""
        col_a = MagicMock()
        col_a.name = "id"
        col_b = MagicMock()
        col_b.name = "name"

        mock_table = MagicMock()
        mock_table.columns = [col_a, col_b]

        obj = MagicMock()
        obj.__table__ = mock_table
        # Remove model_dump so the Pydantic branch is not taken
        del obj.model_dump
        obj.id = 1
        obj.name = "test"
        # Plain values have no .value or .isoformat
        type(obj).id = property(lambda self: 1)
        type(obj).name = property(lambda self: "test")

        # Rebuild without properties to keep it simple
        obj2 = MagicMock(spec=[])
        obj2.__table__ = mock_table
        obj2.id = 1
        obj2.name = "test"

        result = _serialize(obj2)
        assert result == {"id": 1, "name": "test"}

    def test_sqlalchemy_model_with_enum_field(self):
        """Enum fields in SQLAlchemy models are converted via .value."""

        class Status(enum.Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        col = MagicMock()
        col.name = "status"
        mock_table = MagicMock()
        mock_table.columns = [col]

        obj = MagicMock(spec=[])
        obj.__table__ = mock_table
        obj.status = Status.ACTIVE

        result = _serialize(obj)
        assert result == {"status": "active"}

    def test_sqlalchemy_model_with_datetime_field(self):
        """Datetime fields are serialized via .isoformat()."""
        dt = datetime(2026, 2, 7, 12, 0, 0)

        col = MagicMock()
        col.name = "created_at"
        mock_table = MagicMock()
        mock_table.columns = [col]

        obj = MagicMock(spec=[])
        obj.__table__ = mock_table
        obj.created_at = dt

        result = _serialize(obj)
        assert result == {"created_at": "2026-02-07T12:00:00"}

    def test_bare_enum(self):
        """Bare enum values (not in a model) are converted via .value."""

        class Color(enum.Enum):
            RED = "red"
            BLUE = "blue"

        assert _serialize(Color.RED) == "red"
        assert _serialize(Color.BLUE) == "blue"

    def test_list_of_sqlalchemy_models(self):
        """Lists of SQLAlchemy models are serialized element-wise."""
        col = MagicMock()
        col.name = "id"
        mock_table = MagicMock()
        mock_table.columns = [col]

        obj1 = MagicMock(spec=[])
        obj1.__table__ = mock_table
        obj1.id = 1

        obj2 = MagicMock(spec=[])
        obj2.__table__ = mock_table
        obj2.id = 2

        result = _serialize([obj1, obj2])
        assert result == [{"id": 1}, {"id": 2}]

    def test_dict_with_enum_values(self):
        """Dict values that are enums get serialized."""

        class Mode(enum.Enum):
            FAST = "fast"

        result = _serialize({"mode": Mode.FAST})
        assert result == {"mode": "fast"}


# ---------------------------------------------------------------------------
# _respond
# ---------------------------------------------------------------------------

class TestRespond:
    """Unit tests for the _respond helper."""

    @pytest.mark.asyncio
    async def test_respond_with_data(self, mock_ws):
        await _respond(mock_ws, "req-1", data={"key": "value"})
        assert len(mock_ws.sent_messages) == 1
        msg = mock_ws.sent_messages[0]
        assert msg["id"] == "req-1"
        assert msg["data"] == {"key": "value"}
        assert msg["error"] is None

    @pytest.mark.asyncio
    async def test_respond_with_error(self, mock_ws):
        await _respond(mock_ws, "req-2", error="something failed")
        msg = mock_ws.sent_messages[0]
        assert msg["id"] == "req-2"
        assert msg["data"] is None
        assert msg["error"] == "something failed"

    @pytest.mark.asyncio
    async def test_respond_with_none_id(self, mock_ws):
        await _respond(mock_ws, None, data="ok")
        msg = mock_ws.sent_messages[0]
        assert msg["id"] is None
        assert msg["data"] == "ok"

    @pytest.mark.asyncio
    async def test_respond_serializes_data(self, mock_ws):
        """Data passed to _respond is run through _serialize."""

        class Priority(enum.Enum):
            HIGH = "high"

        await _respond(mock_ws, "req-3", data=Priority.HIGH)
        msg = mock_ws.sent_messages[0]
        assert msg["data"] == "high"

    @pytest.mark.asyncio
    async def test_respond_calls_send_json(self, mock_ws):
        await _respond(mock_ws, "req-4", data="hi")
        mock_ws.send_json.assert_awaited_once()


# ---------------------------------------------------------------------------
# _save_disk_partition / _remove_disk_partition
# ---------------------------------------------------------------------------

class TestDiskPartitionPersistence:
    """Tests for saving and removing disk partitions from the JSON file."""

    @pytest.fixture
    def fake_home(self, tmp_path):
        """Patch Path.home() to return tmp_path so we don't touch the real home dir."""
        with patch("app.api.ws_handler.Path.home", return_value=tmp_path):
            yield tmp_path

    def _partitions_file(self, home):
        return home / ".ktizo" / "data" / "disk_partitions.json"

    def test_save_creates_file_and_dirs(self, fake_home):
        _save_disk_partition("/var/mnt/longhorn", "/dev/sda1")
        pf = self._partitions_file(fake_home)
        assert pf.exists()
        data = json.loads(pf.read_text())
        assert len(data) == 1
        assert data[0]["mountpoint"] == "/var/mnt/longhorn"
        assert data[0]["disk"] == "/dev/sda1"

    def test_save_appends_without_duplicating(self, fake_home):
        _save_disk_partition("/var/mnt/longhorn", "/dev/sda1")
        _save_disk_partition("/var/mnt/longhorn", "/dev/sda1")  # duplicate
        data = json.loads(self._partitions_file(fake_home).read_text())
        assert len(data) == 1

    def test_save_multiple_different_partitions(self, fake_home):
        _save_disk_partition("/var/mnt/longhorn", "/dev/sda1")
        _save_disk_partition("/var/mnt/ceph", "/dev/sdb1")
        data = json.loads(self._partitions_file(fake_home).read_text())
        assert len(data) == 2
        mountpoints = {p["mountpoint"] for p in data}
        assert mountpoints == {"/var/mnt/longhorn", "/var/mnt/ceph"}

    def test_save_with_empty_disk(self, fake_home):
        _save_disk_partition("/var/mnt/test")
        data = json.loads(self._partitions_file(fake_home).read_text())
        assert data[0]["disk"] == ""

    def test_save_handles_corrupt_json(self, fake_home):
        """If the file contains invalid JSON, it starts fresh."""
        pf = self._partitions_file(fake_home)
        pf.parent.mkdir(parents=True, exist_ok=True)
        pf.write_text("NOT VALID JSON {{{")
        _save_disk_partition("/var/mnt/longhorn", "/dev/sda1")
        data = json.loads(pf.read_text())
        assert len(data) == 1

    def test_remove_from_existing(self, fake_home):
        _save_disk_partition("/var/mnt/longhorn", "/dev/sda1")
        _save_disk_partition("/var/mnt/ceph", "/dev/sdb1")
        _remove_disk_partition("/var/mnt/longhorn")
        data = json.loads(self._partitions_file(fake_home).read_text())
        assert len(data) == 1
        assert data[0]["mountpoint"] == "/var/mnt/ceph"

    def test_remove_nonexistent_mountpoint(self, fake_home):
        _save_disk_partition("/var/mnt/longhorn", "/dev/sda1")
        _remove_disk_partition("/var/mnt/nonexistent")
        data = json.loads(self._partitions_file(fake_home).read_text())
        assert len(data) == 1

    def test_remove_when_file_missing(self, fake_home):
        """Removing from a non-existent file should not raise."""
        _remove_disk_partition("/var/mnt/longhorn")  # no error

    def test_remove_last_partition_leaves_empty_list(self, fake_home):
        _save_disk_partition("/var/mnt/longhorn", "/dev/sda1")
        _remove_disk_partition("/var/mnt/longhorn")
        data = json.loads(self._partitions_file(fake_home).read_text())
        assert data == []


# ---------------------------------------------------------------------------
# _disk_name_from_path
# ---------------------------------------------------------------------------

class TestDiskNameFromPath:
    """Tests for generating Longhorn disk names from mount paths."""

    def test_standard_path(self):
        assert _disk_name_from_path("/var/mnt/longhorn") == "disk-var-mnt-longhorn"

    def test_trailing_slash(self):
        assert _disk_name_from_path("/var/mnt/longhorn/") == "disk-var-mnt-longhorn"

    def test_leading_and_trailing_slashes(self):
        assert _disk_name_from_path("/data/") == "disk-data"

    def test_deep_path(self):
        assert _disk_name_from_path("/a/b/c/d") == "disk-a-b-c-d"

    def test_single_segment(self):
        assert _disk_name_from_path("/data") == "disk-data"

    def test_dot_in_path(self):
        assert _disk_name_from_path("/var/mnt/disk.1") == "disk-var-mnt-disk-1"

    def test_empty_string(self):
        assert _disk_name_from_path("") == "disk-default"

    def test_just_slash(self):
        assert _disk_name_from_path("/") == "disk-default"

    def test_no_leading_slash(self):
        assert _disk_name_from_path("var/mnt/longhorn") == "disk-var-mnt-longhorn"
