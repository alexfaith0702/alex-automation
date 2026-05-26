"""
API tests for GET /api/query  (+ health check)

Covers:
  - Authorization (no token / bad token / wrong scheme)
  - Query filters (keyword, category, combined, case‑insensitive)
  - Response schema validation
  - Data‑driven scenarios from query_cases.json
  - A deliberately failing test (to demonstrate log capture in Allure)

Uses: ``auth_client`` (function‑scoped, token pre‑set),
      ``unauth_client`` for 401 tests.
"""
import json
import allure
from common.logger import get_logger

log = get_logger()


@allure.feature("QueryItems")
class TestQuery:
    """Tests for the /api/query endpoint."""

    # ==================================================================
    # Authorization
    # ==================================================================
    @allure.story("Authorization")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("Requests without a valid Bearer token must be rejected with 401.")
    def test_query_without_token_returns_401(self, unauth_client):
        """No Authorization header → 401."""
        with allure.step("GET /api/query without Authorization header"):
            resp = unauth_client.get("/api/query")

        with allure.step("Assert 401"):
            body = resp.json()
            assert resp.status_code == 401
            assert body["code"] == 401
            assert body["msg"] == "Unauthorized"

    @allure.story("Authorization")
    def test_query_with_bad_token(self, unauth_client):
        """Wrong Bearer token → 401."""
        unauth_client.token = "bad-fake-token"
        resp = unauth_client.get("/api/query")
        assert resp.status_code == 401
        log.info("Bad token correctly rejected")

    @allure.story("Authorization")
    def test_query_with_wrong_scheme(self, unauth_client):
        """Non‑Bearer auth → 401."""
        resp = unauth_client.get(
            "/api/query",
            headers={"Authorization": "Basic YWRtaW46cGFzc3dvcmQ="},
        )
        assert resp.status_code == 401
        log.info("Basic auth scheme correctly rejected")

    # ==================================================================
    # Successful queries
    # ==================================================================
    @allure.story("Query with valid token")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_query_all_items(self, auth_client):
        """No filters → returns all 4 items."""
        with allure.step("GET /api/query (no params)"):
            resp = auth_client.get("/api/query")

        with allure.step("Assert 4 items returned"):
            body = resp.json()
            assert body["code"] == 200
            items = body["data"]
            assert len(items) == 4
            log.info(f"All-items query returned {len(items)} items")

    @allure.story("Query with valid token")
    def test_query_filter_by_keyword(self, auth_client):
        """keyword=Apple → 1 item named 'Apple'."""
        resp = auth_client.get("/api/query", params={"keyword": "Apple"})
        items = resp.json()["data"]
        assert len(items) == 1
        assert items[0]["name"] == "Apple"

    @allure.story("Query with valid token")
    def test_query_filter_by_category(self, auth_client):
        """category=fruit → Apple + Banana."""
        resp = auth_client.get("/api/query", params={"category": "fruit"})
        data = resp.json()["data"]
        names = {it["name"] for it in data}
        assert names == {"Apple", "Banana"}
        log.info(f"Fruit category returned: {names}")

    @allure.story("Query with valid token")
    def test_query_case_insensitive_keyword(self, auth_client):
        """keyword=apple (lowercase) still matches 'Apple'."""
        resp = auth_client.get("/api/query", params={"keyword": "apple"})
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name"] == "Apple"
        log.debug("Case-insensitive keyword filter works")

    @allure.story("Query with valid token")
    def test_query_case_insensitive_category(self, auth_client):
        """category=ELECTRONICS (uppercase) still matches."""
        resp = auth_client.get("/api/query", params={"category": "ELECTRONICS"})
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name"] == "Laptop"

    @allure.story("Query with valid token")
    def test_query_no_match(self, auth_client):
        """Non‑matching keyword → empty list."""
        resp = auth_client.get("/api/query", params={"keyword": "ZZZNotFound"})
        data = resp.json()["data"]
        assert data == []
        log.info("No-match query correctly returned empty list")

    @allure.story("Query with valid token")
    def test_query_combined_filters(self, auth_client):
        """keyword + category together."""
        resp = auth_client.get(
            "/api/query",
            params={"keyword": "Banana", "category": "fruit"},
        )
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name"] == "Banana"

    # ==================================================================
    # Response schema
    # ==================================================================
    @allure.story("Response schema")
    @allure.severity(allure.severity_level.NORMAL)
    def test_item_schema(self, auth_client):
        """Every item must have id(int), name(str), category(str), price(number)."""
        resp = auth_client.get("/api/query")
        items = resp.json()["data"]
        for item in items:
            with allure.step(f"Validate schema of item id={item.get('id')}"):
                assert isinstance(item["id"], int), f"id should be int, got {type(item['id'])}"
                assert isinstance(item["name"], str)
                assert isinstance(item["category"], str)
                assert isinstance(item["price"], (int, float))
        log.info(f"Schema validated for {len(items)} items")

    # ==================================================================
    # Data‑driven from query_cases.json
    # ==================================================================
    @allure.story("Data-driven query")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description(
        "Uses ``test_data/query_cases.json`` to drive multiple filter "
        "combinations.  Each JSON case declares expected count and "
        "optional expected item names."
    )
    def test_query_data_driven(self, auth_client, query_test_cases):
        """Iterate cases from query_cases.json."""
        for idx, case in enumerate(query_test_cases, 1):
            with allure.step(f"[{idx}/{len(query_test_cases)}] Case: {case['name']}"):
                params = {}
                if case.get("keyword"):
                    params["keyword"] = case["keyword"]
                if case.get("category"):
                    params["category"] = case["category"]

                resp = auth_client.get("/api/query", params=params)
                body = resp.json()

                assert resp.status_code == 200
                items = body["data"]
                assert len(items) == case["expect_count"], (
                    f"[{case['name']}] Expected {case['expect_count']} items,"
                    f" got {len(items)}"
                )

                if "expect_names" in case:
                    actual_names = [it["name"] for it in items]
                    assert sorted(actual_names) == sorted(case["expect_names"]), (
                        f"[{case['name']}] Expected names {case['expect_names']},"
                        f" got {actual_names}"
                    )

                log.info(f"  ✓ {case['name']} — {len(items)} items")

        log.info(f"Data-driven query test complete ({len(query_test_cases)} cases)")

    # ==================================================================
    # DELIBERATELY FAILING TEST — demonstrates log capture in Allure
    # ==================================================================
    @allure.story("Negative demo")
    @allure.severity(allure.severity_level.MINOR)
    @allure.description(
        "**This test is designed to FAIL.**\n\n"
        "It intentionally makes a wrong assertion (expecting 99 items "
        "when only 4 exist) to demonstrate:\n"
        "- Full request / response log captured in the Allure report\n"
        "- Execution log with DEBUG-level detail of every HTTP call\n"
        "- The exact assertion error message + stack trace\n\n"
        "Remove this test in production."
    )
    def test_FAILING_demo_incorrect_item_count(self, auth_client):
        """[DEMO] Intentional wrong assertion to show failure logging."""
        log.warning("=== This test is DESIGNED to fail — demo of log capture ===")

        with allure.step("Step 1 — Send valid query"):
            resp = auth_client.get("/api/query")
            body = resp.json()
            actual_count = len(body["data"])
            log.info(f"Received {actual_count} items from /api/query")
            log.debug(f"Response body: {json.dumps(body, indent=2)}")

        with allure.step("Step 2 — Make WRONG assertion (expect 99, have 4)"):
            log.error(f"About to assert 99 items, but only {actual_count} exist!")
            # 👇 This assertion intentionally fails
            assert actual_count == 99, (
                f"[EXPECTED FAILURE] The API returned {actual_count} items "
                f"but we (wrongly) expected 99.  This is a demo."
            )

        log.info("This line will never execute because the assertion above fails")


# ============================================================================
# Standalone — health check (no auth required)
# ============================================================================
@allure.feature("Health")
class TestHealth:
    """Tests for /api/health."""

    @allure.story("Health check")
    @allure.severity(allure.severity_level.NORMAL)
    def test_health_endpoint(self, http_client):
        """GET /api/health → 200 + 'healthy'."""
        with allure.step("GET /api/health"):
            resp = http_client.get("/api/health")

        with allure.step("Assert healthy"):
            body = resp.json()
            assert resp.status_code == 200
            assert body["code"] == 200
            assert body["data"]["status"] == "healthy"

        log.info("Health check passed")
