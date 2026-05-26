"""
One-shot test runner — runs all tests with Allure output, then generates
a browser-viewable HTML report (no Java required).

Usage:
    python run_tests.py                  # run all tests
    python run_tests.py -m smoke         # only smoke tests
    python run_tests.py -k "login"       # only tests matching "login"
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "reports" / "allure-results"
REPORT_DIR = ROOT / "reports" / "allure-report"

# ---- Pass extra args through to pytest ----
pytest_args = sys.argv[1:] if len(sys.argv) > 1 else []

cmd = [
    sys.executable, "-m", "pytest", "test_api/",
    "-v",
    f"--alluredir={RESULTS_DIR}",
] + pytest_args

print("=" * 60)
print("Running tests...")
print("=" * 60)
result = subprocess.run(cmd, cwd=str(ROOT))

print()
print("=" * 60)
print("Generating HTML report...")
print("=" * 60)

# Use our Java-free report generator
from common.allure_report import build_report

build_report(str(RESULTS_DIR), str(REPORT_DIR))
print()
print(f"Open report: file:///{str((REPORT_DIR / 'index.html').resolve()).replace('\\', '/')}")

sys.exit(result.returncode)
