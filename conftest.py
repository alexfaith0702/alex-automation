"""
Root conftest.py — session‑scoped fixtures shared by every test module.

Provides:
  - Server startup in a background thread (so we can test with real HTTP)
  - Logger singleton configured once per session
  - Test‑data loaders (JSON files)
"""
import json
import os
import socket
import threading
import time
import sys

import allure
import pytest

from common.logger import LogManager
from common.http_client import HttpClient


# ============================================================================
# Import the Flask app early so we can start / stop it
# ============================================================================
# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(__file__))
from app import app as _flask_app


# ============================================================================
# Logger — session‑scoped, configured once
# ============================================================================
@pytest.fixture(scope="session", autouse=True)
def global_logger():
    """Configure the singleton logger at the start of the session."""
    mgr = LogManager.get_instance()
    mgr.configure(
        name="api_test",
        level="DEBUG",
        log_dir=os.path.join(os.path.dirname(__file__), "reports", "logs"),
        console=True,
        file=True,
    )
    log = mgr.logger
    log.info("=" * 60)
    log.info("Test session started")
    log.info("=" * 60)
    yield log
    log.info("=" * 60)
    log.info("Test session ended")
    log.info("=" * 60)
    LogManager.reset()


# ============================================================================
# Free-port helper
# ============================================================================
def _find_free_port(start: int = 5000, end: int = 5099) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"No free port in range {start}-{end}")


# ============================================================================
# Live server fixture — starts Flask in a background thread
# ============================================================================
@pytest.fixture(scope="session")
def app_server():
    """Start the Flask app on a free port in a daemon thread.

    Yields a base URL like ``http://127.0.0.1:5042``.
    The server is torn down automatically when the session ends.
    """
    port = _find_free_port()
    host = "127.0.0.1"
    base_url = f"http://{host}:{port}"

    _flask_app.config["TESTING"] = True

    def _run():
        _flask_app.run(host=host, port=port, debug=False, use_reloader=False)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    # --- Poll until the server is actually listening ---
    max_wait = 10  # seconds
    for _ in range(max_wait * 10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            if s.connect_ex((host, port)) == 0:
                break
        time.sleep(0.1)
    else:
        raise RuntimeError(f"Flask server did not start within {max_wait}s")

    yield base_url

    # Teardown is implicit — daemon thread dies with the process


# ============================================================================
# HTTP client fixture (session‑scoped)
# ============================================================================
@pytest.fixture(scope="session")
def http_client(app_server, global_logger) -> HttpClient:
    """Return a session‑scoped HttpClient pointed at the live server."""
    import allure

    with allure.step("Create HTTP client"):
        client = HttpClient(base_url=app_server, logger=global_logger, default_timeout=10)

    yield client
    client.close()


# ============================================================================
# Auth helpers — get a token once and reuse
# ============================================================================
@pytest.fixture(scope="session")
def auth_token(http_client) -> str:
    """Log in once and return a valid Bearer token."""
    with allure.step("Obtain auth token for session"):
        resp = http_client.post("/api/login", json={"username": "admin", "password": "password123"})
        body = resp.json()
        token = body["data"]["token"]
        http_client.token = token
    return token


# ============================================================================
# Path helpers
# ============================================================================
@pytest.fixture(scope="session")
def test_data_dir():
    return os.path.join(os.path.dirname(__file__), "test_data")


# ============================================================================
# Data‑driven helpers
# ============================================================================
def _load_json(filepath: str):
    with open(filepath, "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def login_test_cases(test_data_dir):
    return _load_json(os.path.join(test_data_dir, "login_cases.json"))


@pytest.fixture(scope="session")
def query_test_cases(test_data_dir):
    return _load_json(os.path.join(test_data_dir, "query_cases.json"))
