"""Tests for EXP-001 FLUX guidance experiment runner."""
from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub 'requests' before importing run.py so it never needs to be installed.
# call_flux does a lazy `import requests` so we inject a fake module here.
# ---------------------------------------------------------------------------

_requests_stub = ModuleType("requests")
_requests_stub.post = MagicMock()  # replaced per-test via patch
_requests_stub.exceptions = ModuleType("requests.exceptions")
_requests_stub.exceptions.Timeout = TimeoutError
_requests_stub.exceptions.ConnectionError = ConnectionError
sys.modules.setdefault("requests", _requests_stub)
sys.modules.setdefault("requests.exceptions", _requests_stub.exceptions)

EXP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXP_DIR))
import run  # noqa: E402


# ---------------------------------------------------------------------------
# call_flux — dry run
# ---------------------------------------------------------------------------

class TestCallFluxDryRun:
    def test_returns_none(self):
        result = run.call_flux(
            api_key="k",
            endpoint="https://example.com",
            prompt="test",
            image_bytes=b"img",
            guidance=15,
            seed=42,
            dry_run=True,
        )
        assert result is None

    def test_makes_no_http_call(self):
        with patch.object(_requests_stub, "post") as mock_post:
            run.call_flux(
                api_key="k",
                endpoint="https://example.com",
                prompt="test",
                image_bytes=b"img",
                guidance=15,
                seed=42,
                dry_run=True,
            )
            mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# call_flux — success path
# ---------------------------------------------------------------------------

class TestCallFluxSuccess:
    def _make_response(self, image_bytes: bytes) -> MagicMock:
        b64 = base64.b64encode(image_bytes).decode()
        resp = MagicMock()
        resp.ok = True
        resp.json.return_value = {"data": [{"b64_json": b64}]}
        return resp

    def test_returns_decoded_image_bytes(self):
        expected = b"fake-png-data"
        with patch.object(_requests_stub, "post", return_value=self._make_response(expected)):
            result = run.call_flux(
                api_key="key",
                endpoint="https://example.com",
                prompt="p",
                image_bytes=b"src",
                guidance=20,
                seed=42,
            )
        assert result == expected

    def test_sends_correct_guidance_value(self):
        with patch.object(_requests_stub, "post", return_value=self._make_response(b"x")) as mock_post:
            run.call_flux(
                api_key="key",
                endpoint="https://ep.com",
                prompt="p",
                image_bytes=b"src",
                guidance=30,
                seed=42,
            )
        body = mock_post.call_args.kwargs["json"]
        assert body["guidance"] == 30

    def test_sends_correct_seed(self):
        with patch.object(_requests_stub, "post", return_value=self._make_response(b"x")) as mock_post:
            run.call_flux(
                api_key="key",
                endpoint="https://ep.com",
                prompt="p",
                image_bytes=b"src",
                guidance=15,
                seed=99,
            )
        body = mock_post.call_args.kwargs["json"]
        assert body["seed"] == 99

    def test_encodes_image_as_base64(self):
        image = b"raw-image-bytes"
        with patch.object(_requests_stub, "post", return_value=self._make_response(b"x")) as mock_post:
            run.call_flux(
                api_key="key",
                endpoint="https://ep.com",
                prompt="p",
                image_bytes=image,
                guidance=15,
                seed=42,
            )
        body = mock_post.call_args.kwargs["json"]
        assert body["input_image"] == base64.b64encode(image).decode()

    def test_sends_bearer_auth_header(self):
        with patch.object(_requests_stub, "post", return_value=self._make_response(b"x")) as mock_post:
            run.call_flux(
                api_key="secret-key",
                endpoint="https://ep.com",
                prompt="p",
                image_bytes=b"src",
                guidance=15,
                seed=42,
            )
        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer secret-key"

    def test_appends_api_version_to_url(self):
        with patch.object(_requests_stub, "post", return_value=self._make_response(b"x")) as mock_post:
            run.call_flux(
                api_key="k",
                endpoint="https://ep.com/flux",
                prompt="p",
                image_bytes=b"src",
                guidance=15,
                seed=42,
            )
        url = mock_post.call_args.args[0]
        assert url == "https://ep.com/flux?api-version=preview"


# ---------------------------------------------------------------------------
# call_flux — bad response shapes
# ---------------------------------------------------------------------------

class TestCallFluxBadResponse:
    def _resp(self, payload: dict, status: int = 200) -> MagicMock:
        r = MagicMock()
        r.ok = status < 400
        r.status_code = status
        r.json.return_value = payload
        r.text = str(payload)
        return r

    def test_raises_on_missing_data_key(self):
        with patch.object(_requests_stub, "post", return_value=self._resp({})):
            with pytest.raises(RuntimeError, match="Unexpected response shape"):
                run.call_flux(
                    api_key="k", endpoint="https://ep.com",
                    prompt="p", image_bytes=b"src", guidance=15, seed=42,
                )

    def test_raises_on_missing_b64_json(self):
        with patch.object(_requests_stub, "post", return_value=self._resp({"data": [{"url": "x"}]})):
            with pytest.raises(RuntimeError, match="Unexpected response shape"):
                run.call_flux(
                    api_key="k", endpoint="https://ep.com",
                    prompt="p", image_bytes=b"src", guidance=15, seed=42,
                )

    def test_raises_on_non_retryable_4xx(self):
        r = self._resp({"error": "bad request"}, status=400)
        r.raise_for_status.side_effect = Exception("400 Bad Request")
        with patch.object(_requests_stub, "post", return_value=r):
            with pytest.raises(Exception):
                run.call_flux(
                    api_key="k", endpoint="https://ep.com",
                    prompt="p", image_bytes=b"src", guidance=15, seed=42,
                )


# ---------------------------------------------------------------------------
# call_flux — retry behaviour
# ---------------------------------------------------------------------------

class TestCallFluxRetry:
    def test_retries_on_429(self):
        good_b64 = base64.b64encode(b"ok").decode()
        rate_limit = MagicMock()
        rate_limit.ok = False
        rate_limit.status_code = 429
        rate_limit.text = "rate limited"

        success = MagicMock()
        success.ok = True
        success.json.return_value = {"data": [{"b64_json": good_b64}]}

        with patch.object(_requests_stub, "post", side_effect=[rate_limit, success]):
            with patch("time.sleep"):  # don't actually wait
                result = run.call_flux(
                    api_key="k", endpoint="https://ep.com",
                    prompt="p", image_bytes=b"src", guidance=15, seed=42,
                )
        assert result == b"ok"

    def test_exhausts_retries_and_raises(self):
        bad = MagicMock()
        bad.ok = False
        bad.status_code = 503
        bad.text = "service unavailable"

        with patch.object(_requests_stub, "post", return_value=bad):
            with patch("time.sleep"):
                with pytest.raises(RuntimeError, match="FLUX request failed after"):
                    run.call_flux(
                        api_key="k", endpoint="https://ep.com",
                        prompt="p", image_bytes=b"src", guidance=15, seed=42,
                    )


# ---------------------------------------------------------------------------
# CLI — env var validation
# ---------------------------------------------------------------------------

class TestEnvValidation:
    def _run_script(self, env: dict) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(EXP_DIR / "run.py")],
            env={**env},
            capture_output=True,
            text=True,
        )

    def test_exits_1_when_flux_key_missing(self):
        result = self._run_script({"FLUX_ENDPOINT": "https://ep.com", "PATH": "/usr/bin:/bin"})
        assert result.returncode == 1
        assert "FLUX_KEY" in result.stdout

    def test_exits_1_when_flux_endpoint_missing(self):
        result = self._run_script({"FLUX_KEY": "key", "PATH": "/usr/bin:/bin"})
        assert result.returncode == 1
        assert "FLUX_ENDPOINT" in result.stdout

    def test_exits_1_when_both_missing(self):
        result = self._run_script({"PATH": "/usr/bin:/bin"})
        assert result.returncode == 1
        assert "FLUX_KEY" in result.stdout
        assert "FLUX_ENDPOINT" in result.stdout

    def test_reports_both_errors_in_one_message(self):
        result = self._run_script({"PATH": "/usr/bin:/bin"})
        assert "sample.env" in result.stdout

    def test_dry_run_succeeds_without_env_vars(self):
        result = self._run_script({"PATH": "/usr/bin:/bin", **_minimal_path_env(), "PYTHONPATH": str(EXP_DIR)})
        # dry-run flag — pass via subprocess with args
        result2 = subprocess.run(
            [sys.executable, str(EXP_DIR / "run.py"), "--dry-run"],
            env={"PATH": "/usr/bin:/bin", **_minimal_path_env()},
            capture_output=True,
            text=True,
        )
        assert result2.returncode == 0


# ---------------------------------------------------------------------------
# Constants sanity checks
# ---------------------------------------------------------------------------

class TestConstants:
    def test_guidance_values_match_setup_md(self):
        assert run.GUIDANCE_VALUES == [5, 10, 15, 20, 30, 50]

    def test_seed_is_fixed(self):
        assert run.SEED == 42

    def test_input_photos_keys_match_expected_rooms(self):
        assert set(run.INPUT_PHOTOS) == {"kitchen", "living_room"}

    def test_input_photos_point_to_real_files(self):
        missing = [room for room, path in run.INPUT_PHOTOS.items() if not path.exists()]
        assert missing == [], f"Missing input photos for: {missing}"

    def test_style_prompt_is_nonempty(self):
        assert len(run.STYLE_PROMPT) > 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_path_env() -> dict:
    """Return a minimal PATH-like env that lets Python find stdlib."""
    import os
    return {"HOME": os.environ.get("HOME", "/root")}
