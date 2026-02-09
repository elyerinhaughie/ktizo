"""Tests for CI/CD (ARC) monitoring handler functions."""
import json
import time
import pytest
from unittest.mock import AsyncMock, patch

from app.api.ws_handler import _cicd_overview, _cicd_runners, _cicd_listeners
from tests.conftest import get_ws_response


# ---------------------------------------------------------------------------
# Sample kubectl JSON responses
# ---------------------------------------------------------------------------

_SAMPLE_ARS = json.dumps({
    "items": [
        {
            "metadata": {
                "name": "ci-runners",
                "namespace": "arc-runners",
                "creationTimestamp": "2026-02-09T10:00:00Z",
                "annotations": {
                    "actions.github.com/runner-group-name": "Default",
                },
                "labels": {
                    "actions.github.com/scale-set-name": "ci-runners",
                },
            },
            "spec": {
                "githubConfigUrl": "https://github.com/SafeWords",
                "githubConfigSecret": "ci-runners-gha-rs-github-secret",
                "minRunners": 1,
                "maxRunners": 10,
            },
            "status": {
                "currentRunners": 2,
                "pendingEphemeralRunners": 0,
                "runningEphemeralRunners": 2,
            },
        }
    ]
}).encode()

_SAMPLE_CONTROLLER_PODS = json.dumps({
    "items": [
        {
            "metadata": {
                "name": "arc-gha-rs-controller-abc123",
                "namespace": "arc-systems",
                "creationTimestamp": "2026-02-09T08:00:00Z",
            },
            "status": {
                "phase": "Running",
                "containerStatuses": [
                    {"ready": True, "restartCount": 0},
                ],
            },
        }
    ]
}).encode()

_SAMPLE_RUNNERS = json.dumps({
    "items": [
        {
            "metadata": {
                "name": "ci-runners-xyz-runner-abc",
                "namespace": "arc-runners",
                "creationTimestamp": "2026-02-09T12:00:00Z",
                "labels": {
                    "actions.github.com/scale-set-name": "ci-runners",
                },
            },
            "status": {
                "phase": "Running",
                "ready": True,
                "runnerId": 1437,
            },
        },
        {
            "metadata": {
                "name": "ci-runners-xyz-runner-def",
                "namespace": "arc-runners",
                "creationTimestamp": "2026-02-09T12:05:00Z",
                "labels": {
                    "actions.github.com/scale-set-name": "ci-runners",
                },
            },
            "status": {
                "phase": "Pending",
                "ready": False,
                "runnerId": 0,
            },
        },
    ]
}).encode()

_SAMPLE_LISTENER_PODS = json.dumps({
    "items": [
        {
            "metadata": {
                "name": "ci-runners-69889744-listener",
                "namespace": "arc-systems",
                "creationTimestamp": "2026-02-09T10:00:00Z",
                "labels": {
                    "actions.github.com/scale-set-name": "ci-runners",
                },
            },
            "status": {
                "phase": "Running",
                "containerStatuses": [
                    {"ready": True, "restartCount": 0},
                ],
            },
        }
    ]
}).encode()

_EMPTY_LIST = json.dumps({"items": []}).encode()


# ---------------------------------------------------------------------------
# Helper to mock subprocess for kubectl
# ---------------------------------------------------------------------------

def _make_proc(stdout: bytes, returncode: int = 0, stderr: bytes = b""):
    """Create a mock subprocess that returns given output."""
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


# ---------------------------------------------------------------------------
# cicd.overview
# ---------------------------------------------------------------------------

class TestCicdOverview:

    @pytest.mark.asyncio
    async def test_overview_kubectl_not_found(self, mock_ws):
        """Returns error when kubectl is not found."""
        with patch("app.api.ws_handler._find_kubectl", return_value=None):
            await _cicd_overview({}, mock_ws, "req-1")

        data, error = get_ws_response(mock_ws)
        assert error == "kubectl not found or query failed"

    @pytest.mark.asyncio
    async def test_overview_success(self, mock_ws):
        """Returns parsed controller and runner set data."""
        proc_rs = _make_proc(_SAMPLE_ARS)
        proc_ctrl = _make_proc(_SAMPLE_CONTROLLER_PODS)
        call_count = 0

        async def mock_create_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # First call = runner sets, second = controller pods
            if call_count == 1:
                return proc_rs
            return proc_ctrl

        with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"), \
             patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess):
            await _cicd_overview({}, mock_ws, "req-2")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert data["controller"]["healthy"] is True
        assert len(data["controller"]["pods"]) == 1
        assert data["controller"]["pods"][0]["name"] == "arc-gha-rs-controller-abc123"
        assert data["controller"]["pods"][0]["status"] == "Running"

        assert len(data["runner_sets"]) == 1
        rs = data["runner_sets"][0]
        assert rs["name"] == "ci-runners"
        assert rs["namespace"] == "arc-runners"
        assert rs["github_config_url"] == "https://github.com/SafeWords"
        assert rs["github_config_secret"] == "ci-runners-gha-rs-github-secret"
        assert rs["runner_group"] == "Default"
        assert rs["min_runners"] == 1
        assert rs["max_runners"] == 10
        assert rs["current_runners"] == 2
        assert rs["running_runners"] == 2
        assert rs["pending_runners"] == 0

    @pytest.mark.asyncio
    async def test_overview_no_runner_sets(self, mock_ws):
        """Returns empty runner_sets when none exist."""
        proc_rs = _make_proc(_EMPTY_LIST)
        proc_ctrl = _make_proc(_SAMPLE_CONTROLLER_PODS)
        call_count = 0

        async def mock_create_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return proc_rs if call_count == 1 else proc_ctrl

        with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"), \
             patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess):
            await _cicd_overview({}, mock_ws, "req-3")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert data["runner_sets"] == []
        assert data["controller"]["healthy"] is True

    @pytest.mark.asyncio
    async def test_overview_controller_unhealthy(self, mock_ws):
        """Controller shows unhealthy when no pods are ready."""
        unhealthy_pods = json.dumps({
            "items": [{
                "metadata": {"name": "ctrl-pod", "namespace": "arc-systems", "creationTimestamp": "2026-02-09T08:00:00Z"},
                "status": {
                    "phase": "Pending",
                    "containerStatuses": [{"ready": False, "restartCount": 5}],
                },
            }]
        }).encode()

        proc_rs = _make_proc(_EMPTY_LIST)
        proc_ctrl = _make_proc(unhealthy_pods)
        call_count = 0

        async def mock_create_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return proc_rs if call_count == 1 else proc_ctrl

        with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"), \
             patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess):
            await _cicd_overview({}, mock_ws, "req-4")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert data["controller"]["healthy"] is False
        assert data["controller"]["pods"][0]["restarts"] == 5

    @pytest.mark.asyncio
    async def test_overview_subprocess_failure(self, mock_ws):
        """Returns error when kubectl fails for runner sets."""
        proc_rs = _make_proc(b"", returncode=1, stderr=b"connection refused")
        proc_ctrl = _make_proc(_EMPTY_LIST)
        call_count = 0

        async def mock_create_subprocess(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return proc_rs if call_count == 1 else proc_ctrl

        with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"), \
             patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess):
            await _cicd_overview({}, mock_ws, "req-5")

        data, error = get_ws_response(mock_ws)
        assert error == "kubectl not found or query failed"


# ---------------------------------------------------------------------------
# cicd.runners
# ---------------------------------------------------------------------------

class TestCicdRunners:

    @pytest.mark.asyncio
    async def test_runners_success(self, mock_ws):
        """Returns parsed ephemeral runners."""
        proc = _make_proc(_SAMPLE_RUNNERS)

        with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"), \
             patch("asyncio.create_subprocess_exec", return_value=proc):
            await _cicd_runners({}, mock_ws, "req-6")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert len(data) == 2
        assert data[0]["name"] == "ci-runners-xyz-runner-abc"
        assert data[0]["phase"] == "Running"
        assert data[0]["ready"] is True
        assert data[0]["runner_id"] == 1437
        assert data[0]["scale_set_name"] == "ci-runners"
        assert data[1]["phase"] == "Pending"
        assert data[1]["ready"] is False

    @pytest.mark.asyncio
    async def test_runners_filter_by_scale_set(self, mock_ws):
        """Passes label selector when scale_set_name is provided."""
        proc = _make_proc(_SAMPLE_RUNNERS)
        captured_args = []

        async def capture_exec(*args, **kwargs):
            captured_args.extend(args)
            return proc

        with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"), \
             patch("asyncio.create_subprocess_exec", side_effect=capture_exec):
            await _cicd_runners({"scale_set_name": "ci-runners"}, mock_ws, "req-7")

        data, error = get_ws_response(mock_ws)
        assert error is None
        # Verify the label selector was passed in the kubectl command
        assert any("actions.github.com/scale-set-name=ci-runners" in str(a) for a in captured_args)

    @pytest.mark.asyncio
    async def test_runners_empty(self, mock_ws):
        """Returns empty list when no runners exist."""
        proc = _make_proc(_EMPTY_LIST)

        with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"), \
             patch("asyncio.create_subprocess_exec", return_value=proc):
            await _cicd_runners({}, mock_ws, "req-8")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert data == []

    @pytest.mark.asyncio
    async def test_runners_kubectl_not_found(self, mock_ws):
        """Returns error when kubectl is not found."""
        with patch("app.api.ws_handler._find_kubectl", return_value=None):
            await _cicd_runners({}, mock_ws, "req-9")

        data, error = get_ws_response(mock_ws)
        assert error == "kubectl not found or query failed"


# ---------------------------------------------------------------------------
# cicd.listeners
# ---------------------------------------------------------------------------

class TestCicdListeners:

    @pytest.mark.asyncio
    async def test_listeners_success(self, mock_ws):
        """Returns parsed listener pods."""
        proc = _make_proc(_SAMPLE_LISTENER_PODS)

        with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"), \
             patch("asyncio.create_subprocess_exec", return_value=proc):
            await _cicd_listeners({}, mock_ws, "req-10")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert len(data) == 1
        assert data[0]["name"] == "ci-runners-69889744-listener"
        assert data[0]["scale_set_name"] == "ci-runners"
        assert data[0]["status"] == "Running"
        assert data[0]["ready"] is True

    @pytest.mark.asyncio
    async def test_listeners_empty(self, mock_ws):
        """Returns empty list when no listener pods exist."""
        proc = _make_proc(_EMPTY_LIST)

        with patch("app.api.ws_handler._find_kubectl", return_value="/usr/local/bin/kubectl"), \
             patch("asyncio.create_subprocess_exec", return_value=proc):
            await _cicd_listeners({}, mock_ws, "req-11")

        data, error = get_ws_response(mock_ws)
        assert error is None
        assert data == []

    @pytest.mark.asyncio
    async def test_listeners_kubectl_not_found(self, mock_ws):
        """Returns error when kubectl is not found."""
        with patch("app.api.ws_handler._find_kubectl", return_value=None):
            await _cicd_listeners({}, mock_ws, "req-12")

        data, error = get_ws_response(mock_ws)
        assert error == "kubectl not found or query failed"
