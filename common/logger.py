"""
LogManager — Encapsulated logging module.

Provides:
  - Dual output: console (coloured) + rotating file
  - pytest integration: captured logs forwarded to Allure on failure
  - Global singleton logger for the whole test suite
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(module)s.%(funcName)s:%(lineno)d | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ---------------------------------------------------------------------------
# AllureLogHandler — buffers log records so we can attach them on failure
# ---------------------------------------------------------------------------
class AllureLogHandler(logging.Handler):
    """In-memory ring buffer of log records, consumed by Allure hooks."""

    def __init__(self, capacity: int = 500):
        super().__init__()
        self.capacity = capacity
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord):
        self.records.append(record)
        if len(self.records) > self.capacity:
            self.records = self.records[-self.capacity:]

    def clear(self):
        self.records.clear()

    def format_all(self) -> str:
        fmt = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        return "\n".join(fmt.format(r) for r in self.records)


# ---------------------------------------------------------------------------
# LogManager
# ---------------------------------------------------------------------------
class LogManager:
    """Singleton log manager — configure once, use everywhere."""

    _instance: Optional["LogManager"] = None

    def __init__(self):
        if LogManager._instance is not None:
            raise RuntimeError("Use LogManager.get_instance()")
        self._logger: Optional[logging.Logger] = None
        self._allure_handler: Optional[AllureLogHandler] = None
        self._file_handler: Optional[logging.Handler] = None

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------
    @classmethod
    def get_instance(cls) -> "LogManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Teardown helper — remove all handlers and reset singleton."""
        if cls._instance and cls._instance._logger:
            for h in list(cls._instance._logger.handlers):
                cls._instance._logger.removeHandler(h)
        cls._instance = None

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def configure(
        self,
        name: str = "api_test",
        level: int = logging.DEBUG,
        log_dir: str = "reports/logs",
        console: bool = True,
        file: bool = True,
    ) -> logging.Logger:
        """Set up the root test logger.

        Parameters
        ----------
        name : str
            Logger name (appears in Allure attachments).
        level : int
            Log level (DEBUG, INFO, …).
        log_dir : str
            Directory for the rotating log file.
        console : bool
            Enable coloured console output.
        file : bool
            Enable rotating file output.
        """
        if self._logger is not None:
            return self._logger  # already configured

        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._logger.handlers.clear()
        self._logger.propagate = False  # don't double-log via root

        # --- Console handler (coloured) ---
        if console:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(level)
            ch.setFormatter(_ColouredFormatter(LOG_FORMAT, datefmt=DATE_FORMAT))
            self._logger.addHandler(ch)

        # --- Rotating file handler ---
        if file:
            os.makedirs(log_dir, exist_ok=True)
            fh = logging.handlers.RotatingFileHandler(
                os.path.join(log_dir, "test_run.log"),
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5,
                encoding="utf-8",
            )
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
            self._logger.addHandler(fh)
            self._file_handler = fh

        # --- Allure buffer handler ---
        self._allure_handler = AllureLogHandler(capacity=500)
        self._allure_handler.setLevel(logging.DEBUG)
        self._logger.addHandler(self._allure_handler)

        return self._logger

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            raise RuntimeError("Logger not configured — call configure() first")
        return self._logger

    @property
    def allure_handler(self) -> Optional[AllureLogHandler]:
        return self._allure_handler

    def get_logs(self) -> str:
        """Return all buffered logs as a formatted string."""
        if self._allure_handler:
            return self._allure_handler.format_all()
        return ""

    def clear_logs(self):
        """Clear the in-memory log buffer (called between tests)."""
        if self._allure_handler:
            self._allure_handler.clear()


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------
def get_logger() -> logging.Logger:
    """Return the singleton test logger (auto‑configure if needed)."""
    mgr = LogManager.get_instance()
    try:
        return mgr.logger
    except RuntimeError:
        # Not yet configured — set up with sensible defaults
        return mgr.configure(name="api_test", level="DEBUG")


# ---------------------------------------------------------------------------
# Coloured console formatter (works cross-platform)
# ---------------------------------------------------------------------------
class _ColouredFormatter(logging.Formatter):
    COLOURS = {
        logging.DEBUG:    "\033[36m",  # cyan
        logging.INFO:     "\033[32m",  # green
        logging.WARNING:  "\033[33m",  # yellow
        logging.ERROR:    "\033[31m",  # red
        logging.CRITICAL: "\033[35m",  # magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        colour = self.COLOURS.get(record.levelno, "")
        record.levelname = f"{colour}{record.levelname}{self.RESET}"
        return super().format(record)
