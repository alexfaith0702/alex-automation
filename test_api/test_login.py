"""
API tests for POST /api/login

Covers:
  - Successful login with valid credentials
  - Failed login with invalid / empty credentials
  - Response schema validation
  - Data‑driven tests from login_cases.json

Uses: ``http_client`` (session‑scoped, no token pre-set).
"""
import json
import allure
from common.logger import get_logger

log = get_logger()


@allure.feature("Login")
class TestLogin:
    """Tests for the /api/login endpoint."""

    # ==================================================================
    # Valid credentials
    # ==================================================================
    @allure.story("Valid credentials")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Verify that a registered user can log in and receive a valid token.")
    def test_valid_login_admin(self, http_client):
        """admin / password123 → 200 + token."""
        payload = {"username": "admin", "password": "password123"}

        with allure.step("POST /api/login as admin"):
            resp = http_client.post("/api/login", json=payload)

        with allure.step("Assert response structure"):
            body = resp.json()
            assert resp.status_code == 200
            assert body["code"] == 200
            assert body["msg"] == "success"
            assert body["data"]["token"] == "test-token-abc123"
            assert body["data"]["username"] == "admin"

        log.info("test_valid_login_admin PASSED")

    @allure.story("Valid credentials")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_valid_login_testuser(self, http_client):
        """testuser / testpass → 200 + token."""
        with allure.step("POST /api/login as testuser"):
            resp = http_client.post(
                "/api/login",
                json={"username": "testuser", "password": "testpass"},
            )

        with allure.step("Assert username is correct"):
            assert resp.status_code == 200
            assert resp.json()["data"]["username"] == "testuser"

    # ==================================================================
    # Invalid credentials
    # ==================================================================
    @allure.story("Invalid credentials")
    @allure.severity(allure.severity_level.NORMAL)
    def test_wrong_password(self, http_client):
        """Correct username but wrong password → 401."""
        with allure.step("POST /api/login with wrong password"):
            resp = http_client.post(
                "/api/login",
                json={"username": "admin", "password": "wrongpass"},
            )

        with allure.step("Assert 401 response"):
            body = resp.json()
            assert resp.status_code == 401
            assert body["code"] == 401
            assert body["data"] is None

        log.debug("401 returned as expected for wrong password")

    @allure.story("Invalid credentials")
    @allure.severity(allure.severity_level.NORMAL)
    def test_wrong_username(self, http_client):
        """Non‑existent username → 401."""
        resp = http_client.post(
            "/api/login",
            json={"username": "nobody", "password": "password123"},
        )
        assert resp.status_code == 401
        log.info("401 returned for unknown user 'nobody'")

    @allure.story("Invalid credentials")
    @allure.severity(allure.severity_level.NORMAL)
    def test_empty_password(self, http_client):
        """Empty password → 401."""
        resp = http_client.post(
            "/api/login",
            json={"username": "admin", "password": ""},
        )
        assert resp.status_code == 401
        log.info("401 returned for empty password")

    @allure.story("Invalid credentials")
    @allure.severity(allure.severity_level.NORMAL)
    def test_empty_username(self, http_client):
        """Empty username → 401."""
        resp = http_client.post(
            "/api/login",
            json={"username": "", "password": "password123"},
        )
        assert resp.status_code == 401

    # ==================================================================
    # Edge cases
    # ==================================================================
    @allure.story("Edge cases")
    @allure.severity(allure.severity_level.MINOR)
    def test_missing_body(self, http_client):
        """Empty POST body → server handles gracefully (400 / 415 / 500)."""
        resp = http_client.post("/api/login", data="")
        assert resp.status_code in (400, 401, 415, 500)
        log.info(f"Empty body returned {resp.status_code}")

    # ==================================================================
    # Data‑driven (JSON file)
    # ==================================================================
    @allure.story("Data-driven")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description(
        "Parameterised test that loops through every case in "
        "``test_data/login_cases.json`` and asserts expected outcome."
    )
    def test_login_data_driven(self, http_client, login_test_cases):
        """Iterate cases from login_cases.json."""
        for idx, case in enumerate(login_test_cases, 1):
            with allure.step(f"[{idx}/{len(login_test_cases)}] Case: {case['name']}"):
                payload = {
                    "username": case["username"],
                    "password": case["password"],
                }
                resp = http_client.post("/api/login", json=payload)
                body = resp.json()

                if case["expect_success"]:
                    assert resp.status_code == 200, (
                        f"[{case['name']}] Expected 200, got {resp.status_code}"
                    )
                    assert body["data"]["token"] == "test-token-abc123"
                    log.info(f"  ✓ {case['name']} — login succeeded")
                else:
                    assert resp.status_code == 401, (
                        f"[{case['name']}] Expected 401, got {resp.status_code}"
                    )
                    log.info(f"  ✓ {case['name']} — correctly rejected")

        log.info(f"Data-driven login test complete ({len(login_test_cases)} cases)")
