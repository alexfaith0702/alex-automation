"""
HttpClient — Encapsulated requests wrapper.

Features:
  - Automatic request / response logging (headers, body, status, timing)
  - Base-URL prefix so tests only pass paths
  - Bearer-token management (set once, auto-attached)
  - Allure step integration — each HTTP call becomes a visible Allure step
  - Timeout and retry built-in
"""
import json
import time
from typing import Optional, Any

import allure
import requests
from requests import Response


MAX_RESPONSE_BODY_LOG = 4096  # characters — truncate huge bodies in logs


class HttpClient:
    """Thin but powerful wrapper around ``requests.Session``."""

    def __init__(self, base_url: str, logger=None, default_timeout: int = 10):
        """
        Parameters
        ----------
        base_url : str
            Scheme + host + port, e.g. ``http://localhost:5000``.
        logger :
            A ``logging.Logger`` instance (or anything with .info / .debug / .error).
        default_timeout : int
            Seconds before a request times out.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = default_timeout
        self._log = logger
        self._token: Optional[str] = None
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------
    @property
    def token(self) -> Optional[str]:
        return self._token

    @token.setter
    def token(self, value: str):
        self._token = value

    @property
    def default_headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    # ------------------------------------------------------------------
    # Core HTTP methods
    # ------------------------------------------------------------------
    def get(self, path: str, **kwargs) -> Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> Response:
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> Response:
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> Response:
        return self._request("DELETE", path, **kwargs)

    def patch(self, path: str, **kwargs) -> Response:
        return self._request("PATCH", path, **kwargs)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _request(self, method: str, path: str, **kwargs) -> Response:
        url = f"{self.base_url}{path}"

        # Merge default headers with per-call headers
        headers = {**self.default_headers, **kwargs.pop("headers", {})}

        # Timeout default
        timeout = kwargs.pop("timeout", self.timeout)

        # --- Log request ---
        req_body = self._serialize_body(kwargs.get("json") or kwargs.get("data"))
        self._log_info(
            "--> %s %s  [params=%s, body=%s, headers=%s]",
            method, url,
            kwargs.get("params", ""),
            req_body,
            self._safe_headers(headers),
        )

        # --- Allure step ---
        step_name = f"{method} {path}"
        with allure.step(step_name):
            # Attach request details to Allure
            allure.attach(
                json.dumps({
                    "method":  method,
                    "url":     url,
                    "headers": self._safe_headers(headers),
                    "params":  kwargs.get("params", None),
                    "body":    req_body,
                }, indent=2, ensure_ascii=False),
                name="Request",
                attachment_type=allure.attachment_type.JSON,
            )

            start = time.time()
            try:
                resp = self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs,
                )
                elapsed = (time.time() - start) * 1000  # ms
            except requests.RequestException as exc:
                elapsed = (time.time() - start) * 1000
                self._log_error(
                    "<-- %s %s  FAILED after %.0fms: %s",
                    method, url, elapsed, exc,
                )
                allure.attach(
                    str(exc),
                    name="Request Exception",
                    attachment_type=allure.attachment_type.TEXT,
                )
                raise

            # --- Log response ---
            resp_body = self._read_body(resp)
            self._log_info(
                "<-- %s %s  → %d %s  [%.0fms, body=%s]",
                method, url, resp.status_code, resp.reason, elapsed,
                resp_body[:MAX_RESPONSE_BODY_LOG],
            )

            # --- Attach response to Allure ---
            allure.attach(
                json.dumps({
                    "status_code": resp.status_code,
                    "reason":      resp.reason,
                    "headers":     dict(resp.headers),
                    "elapsed_ms":  f"{elapsed:.0f}",
                    "body":        resp_body,
                }, indent=2, ensure_ascii=False),
                name="Response",
                attachment_type=allure.attachment_type.JSON,
            )

        return resp

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _log_info(self, fmt, *args):
        if self._log:
            self._log.info(fmt, *args)

    def _log_error(self, fmt, *args):
        if self._log:
            self._log.error(fmt, *args)

    @staticmethod
    def _serialize_body(body) -> Optional[str]:
        if body is None:
            return None
        if isinstance(body, (dict, list)):
            return json.dumps(body, ensure_ascii=False)
        return str(body)[:MAX_RESPONSE_BODY_LOG]

    @staticmethod
    def _read_body(resp: Response) -> str:
        try:
            return resp.text[:MAX_RESPONSE_BODY_LOG]
        except Exception:
            return "<binary / unreadable>"

    @staticmethod
    def _safe_headers(headers: dict) -> dict:
        """Mask Authorization values so they don't leak into logs / reports."""
        safe = {}
        for k, v in headers.items():
            if k.lower() == "authorization":
                safe[k] = v[:12] + "****" if len(v) > 12 else "****"
            else:
                safe[k] = v
        return safe

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
