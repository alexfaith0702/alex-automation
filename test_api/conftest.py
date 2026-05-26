"""
API‑level conftest — fixtures and hooks specific to API testing.

Key responsibilities:
  1. Provide an already-authenticated HttpClient for test functions.
  2. Attach buffered logs + request/response details to Allure on test failure.
  3. Clear the log buffer between tests so each test gets clean logs.
"""
import pytest
import allure

from common.logger import LogManager
from common.http_client import HttpClient


# ============================================================================
# Fixture — authenticated HTTP client
# ============================================================================
@pytest.fixture(scope="function")
def auth_client(http_client, auth_token) -> HttpClient:
    """Return a function‑scoped HttpClient with the token already set.

    Uses the session‑scoped ``http_client`` (shared connection pool) and
    sets the token from ``auth_token`` (fetched once per session).  The
    logger buffer is cleared before each test so logs are isolated.
    """
    mgr = LogManager.get_instance()
    mgr.clear_logs()
    http_client.token = auth_token
    return http_client


# ============================================================================
# Fixture — unauthenticated client (for negative auth tests)
# ============================================================================
@pytest.fixture(scope="function")
def unauth_client(http_client) -> HttpClient:
    """Return a HttpClient WITHOUT a token — used to test 401 paths."""
    mgr = LogManager.get_instance()
    mgr.clear_logs()
    http_client.token = None
    return http_client


# ============================================================================
# Allure hook — attach logs + request/response on test failure
# ============================================================================
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """After each test phase, if the test failed attach:
    - The full log buffer from LogManager
    - Any request/response info stashed on the item
    """
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        mgr = LogManager.get_instance()

        # 1. Attach the complete execution log for this test
        logs = mgr.get_logs()
        if logs:
            allure.attach(
                logs,
                name="Execution Log",
                attachment_type=allure.attachment_type.TEXT,
            )

        # 2. Attach any request/response details stashed during the test
        req_info = getattr(item, "_allure_req_info", None)
        if req_info:
            allure.attach(
                req_info.get("request", "{}"),
                name="Last Request",
                attachment_type=allure.attachment_type.JSON,
            )
            allure.attach(
                req_info.get("response", "{}"),
                name="Last Response",
                attachment_type=allure.attachment_type.JSON,
            )

        # 3. Attach test docstring as test description context
        if item.function.__doc__:
            allure.attach(
                item.function.__doc__.strip(),
                name="Test Description",
                attachment_type=allure.attachment_type.TEXT,
            )
