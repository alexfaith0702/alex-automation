"""
Allure HTML report generator (no Java required).

Reads Allure result JSON files from ``reports/allure-results/`` and
produces a single self-contained HTML file in ``reports/allure-report/``.

Usage:
    python common/allure_report.py

Then open ``reports/allure-report/index.html`` in any browser.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================================
# HTML template
# ============================================================================
HTML_TEMPLATE = r"""\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
  background: #f5f6fa; color: #2d3436; line-height: 1.6;
}}
.header {{
  background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);
  color: #fff; padding: 28px 40px;
}}
.header h1 {{ font-size: 26px; font-weight: 600; }}
.header .meta {{ font-size: 14px; opacity: .85; margin-top: 6px; }}
.summary {{
  display: flex; gap: 20px; padding: 24px 40px; flex-wrap: wrap;
}}
.card {{
  flex: 1; min-width: 140px; background: #fff; border-radius: 12px;
  padding: 20px 24px; box-shadow: 0 2px 12px rgba(0,0,0,.06);
  text-align: center;
}}
.card .num {{ font-size: 36px; font-weight: 700; }}
.card .label {{ font-size: 13px; color: #636e72; margin-top: 4px;
  text-transform: uppercase; letter-spacing: .5px; }}
.card.passed .num {{ color: #00b894; }}
.card.failed .num {{ color: #d63031; }}
.card.broken .num {{ color: #e17055; }}
.card.skipped .num {{ color: #fdcb6e; }}
.card.total .num {{ color: #6c5ce7; }}
.feature {{
  margin: 0 40px 24px; background: #fff; border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,.06); overflow: hidden;
}}
.feature-head {{
  padding: 16px 24px; background: #f8f9fc; border-bottom: 1px solid #eee;
  font-size: 17px; font-weight: 600; display: flex; align-items: center; gap: 10px;
}}
.feature-head .badge {{
  font-size: 12px; padding: 3px 10px; border-radius: 20px; font-weight: 500;
}}
.badge-passed {{ background: #d5f5e3; color: #00b894; }}
.badge-partial {{ background: #ffeaa7; color: #d68910; }}
.badge-failed {{ background: #fadbd8; color: #d63031; }}
.story {{ margin: 8px 20px 16px; }}
.story-title {{
  font-size: 14px; font-weight: 600; color: #636e72; padding: 8px 4px;
  border-bottom: 1px dashed #eee; margin-bottom: 8px;
}}
.test {{
  margin: 6px 0; border: 1px solid #eee; border-radius: 8px; overflow: hidden;
}}
.test-head {{
  padding: 12px 16px; cursor: pointer; display: flex; align-items: center;
  gap: 10px; user-select: none;
}}
.test-head:hover {{ background: #fafafa; }}
.test-head .icon {{ font-size: 18px; flex-shrink: 0; }}
.test-head .name {{ flex: 1; font-size: 14px; font-weight: 500; }}
.test-head .duration {{ font-size: 12px; color: #888; }}
.test-status-passed .test-head {{ border-left: 4px solid #00b894; }}
.test-status-failed .test-head {{ border-left: 4px solid #d63031; background: #fff5f5; }}
.test-status-broken .test-head {{ border-left: 4px solid #e17055; background: #fff5f0; }}
.test-status-skipped .test-head {{ border-left: 4px solid #fdcb6e; background: #fffef5; }}
.test-body {{ display: none; padding: 0 16px 16px; overflow: hidden; }}
.test-body.open {{ display: block; }}
.steps {{ list-style: none; margin-top: 8px; }}
.steps li {{
  padding: 8px 12px; margin: 4px 0; border-radius: 6px;
  font-size: 13px; border-left: 3px solid #ddd;
}}
.steps li.step-passed {{ background: #f0fff5; border-color: #00b894; }}
.steps li.step-failed {{ background: #fff0f0; border-color: #d63031; }}
.steps li.step-broken {{ background: #fff5f0; border-color: #e17055; }}
.steps li.step-skipped {{ background: #fefef5; border-color: #fdcb6e; }}
.step-name {{ font-weight: 500; }}
.step-duration {{ font-size: 12px; color: #888; margin-left: 8px; }}
.attachments {{ margin-top: 8px; }}
.attach-item {{ margin: 6px 0; }}
.attach-toggle {{
  background: #f0f0f5; border: none; padding: 6px 14px; border-radius: 6px;
  cursor: pointer; font-size: 12px; font-weight: 500; color: #6c5ce7;
}}
.attach-toggle:hover {{ background: #e4e4f0; }}
.attach-content {{
  display: none; margin-top: 6px; background: #1e1e2e; color: #cdd6f4;
  border-radius: 6px; padding: 14px;
  font-family: "Fira Code","JetBrains Mono","Cascadia Code",Consolas,monospace;
  font-size: 12px; max-height: 400px; overflow: auto; white-space: pre-wrap;
  word-break: break-all;
}}
.attach-content.open {{ display: block; }}
.error-block {{
  margin: 10px 0; background: #fff0f0; border: 1px solid #fab1a0;
  border-radius: 8px; overflow: hidden;
}}
.error-head {{
  background: #d63031; color: #fff; padding: 8px 14px;
  font-size: 13px; font-weight: 600;
}}
.error-msg {{ padding: 10px 14px; font-size: 13px; color: #d63031; }}
.error-trace {{
  padding: 12px 14px; background: #1e1e2e; color: #cdd6f4;
  font-family: "Fira Code",Consolas,monospace; font-size: 11px;
  max-height: 300px; overflow: auto; white-space: pre-wrap;
}}
.description {{
  margin: 8px 0; padding: 10px 14px; background: #f8f9fc;
  border-radius: 6px; font-size: 13px; color: #636e72;
}}
</style>
</head>
<body>

<div class="header">
  <h1>{title}</h1>
  <div class="meta">Generated at {date} &nbsp;|&nbsp; {total} tests &nbsp;|&nbsp; {duration}</div>
</div>

<div class="summary">
  <div class="card total"><div class="num">{total}</div><div class="label">Total</div></div>
  <div class="card passed"><div class="num">{passed}</div><div class="label">Passed</div></div>
  <div class="card failed"><div class="num">{failed}</div><div class="label">Failed</div></div>
  <div class="card broken"><div class="num">{broken}</div><div class="label">Broken</div></div>
  <div class="card skipped"><div class="num">{skipped}</div><div class="label">Skipped</div></div>
</div>

<div class="content">
{content}
</div>

<script>
document.addEventListener("DOMContentLoaded",function(){{
  document.querySelectorAll(".test-head").forEach(function(h){{
    h.addEventListener("click",function(){{
      this.parentElement.querySelector(".test-body").classList.toggle("open");
    }});
  }});
  document.querySelectorAll(".attach-toggle").forEach(function(b){{
    b.addEventListener("click",function(e){{
      e.stopPropagation();
      this.nextElementSibling.classList.toggle("open");
    }});
  }});
  document.querySelectorAll(".test-status-failed .test-body,.test-status-broken .test-body")
    .forEach(function(b){{b.classList.add("open");}});
}});
</script>
</body>
</html>
"""

# ============================================================================
# Helpers
# ============================================================================
_ICONS = {"passed": "PASS", "failed": "FAIL", "broken": "ERR!", "skipped": "SKIP"}
_STATUS_CLASS = {
    "passed": "test-status-passed",
    "failed": "test-status-failed",
    "broken": "test-status-broken",
    "skipped": "test-status-skipped",
}
_STEP_CLASS = {
    "passed": "step-passed",
    "failed": "step-failed",
    "broken": "step-broken",
    "skipped": "step-skipped",
}


def _load_allure_results(results_dir: Path) -> dict[str, Any]:
    records: dict[str, dict] = {}
    for f in sorted(results_dir.glob("*-result.json")):
        uid = f.stem.replace("-result", "")
        records[uid] = json.loads(f.read_text(encoding="utf-8"))
    return records


def _load_attachment(results_dir: Path, source: str) -> str | None:
    if not source:
        return None
    fpath = results_dir / source
    if fpath.exists():
        try:
            return fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None
    return None


def _render_test(rec: dict, results_dir: Path) -> str:
    status = rec.get("status", "unknown")
    icon = _ICONS.get(status, "?")
    name = rec.get("name", "Unnamed")
    dur = rec.get("time", {}).get("duration", 0) or 0
    dur_str = f"{dur / 1000:.3f}s" if dur else ""

    parts = []
    parts.append(f'<div class="test {_STATUS_CLASS.get(status, "")}">')
    parts.append(
        f'<div class="test-head">'
        f'<span class="icon">{icon}</span>'
        f'<span class="name">{name}</span>'
        f'<span class="duration">{dur_str}</span>'
        f"</div>"
    )
    parts.append('<div class="test-body">')

    # Description
    desc = rec.get("description")
    if desc:
        parts.append(f'<div class="description">{desc}</div>')

    # Steps
    steps = rec.get("steps", [])
    if steps:
        parts.append('<ul class="steps">')
        for step in steps:
            s_status = step.get("status", "unknown")
            s_name = step.get("name", "")
            s_dur = step.get("time", {}).get("duration", 0) or 0
            s_dur_str = f"({s_dur / 1000:.0f}ms)" if s_dur else ""
            parts.append(
                f'<li class="{_STEP_CLASS.get(s_status, "")}">'
                f'<span class="step-name">{s_name}</span>'
                f'<span class="step-duration">{s_dur_str}</span>'
                f"</li>"
            )
        parts.append("</ul>")

    # Attachments
    attachments = rec.get("attachments", [])
    if attachments:
        parts.append('<div class="attachments">')
        for att in attachments:
            att_name = att.get("name", "Attachment")
            source = att.get("source", "")
            att_text = _load_attachment(results_dir, source)
            if att_text:
                escaped = (
                    att_text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                parts.append('<div class="attach-item">')
                parts.append(
                    f'<button class="attach-toggle">{att_name}</button>'
                )
                parts.append(
                    f'<div class="attach-content">{escaped}</div>'
                )
                parts.append("</div>")
        parts.append("</div>")

    # Error for failed / broken
    if status in ("failed", "broken"):
        sd = rec.get("statusDetails", {})
        msg = sd.get("message", "")
        trace = sd.get("trace", "")
        if msg or trace:
            parts.append('<div class="error-block">')
            parts.append('<div class="error-head">Failure Details</div>')
            if msg:
                parts.append(f'<div class="error-msg">{msg}</div>')
            if trace:
                escaped_trace = (
                    trace.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                parts.append(
                    f'<div class="error-trace">{escaped_trace}</div>'
                )
            parts.append("</div>")

    parts.append("</div>")  # /test-body
    parts.append("</div>")  # /test
    return "\n".join(parts)


# ============================================================================
# Main builder
# ============================================================================
def build_report(results_dir: str | Path, output_dir: str | Path):
    results_dir = Path(results_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    records = _load_allure_results(results_dir)
    if not records:
        print("No Allure result files found.")
        return

    stats = {"passed": 0, "failed": 0, "broken": 0, "skipped": 0, "total": 0}
    total_duration_ms = 0

    # Group: feature -> story -> tests
    features: dict[str, dict[str, list[dict]]] = {}

    for uid, rec in records.items():
        status = rec.get("status", "unknown")
        stats["total"] += 1
        if status in stats:
            stats[status] += 1
        total_duration_ms += rec.get("time", {}).get("duration", 0) or 0

        labels = rec.get("labels", [])
        feature_name = "Uncategorised"
        story_name = "Default"
        for lbl in labels:
            if lbl["name"] == "feature":
                feature_name = lbl["value"]
            elif lbl["name"] == "story":
                story_name = lbl["value"]

        features.setdefault(feature_name, {}).setdefault(story_name, []).append(rec)

    content_parts = []
    for feature_name, stories in sorted(features.items()):
        f_stats = {"passed": 0, "failed": 0, "broken": 0, "skipped": 0}
        for story_tests in stories.values():
            for t in story_tests:
                s = t.get("status", "unknown")
                if s in f_stats:
                    f_stats[s] += 1

        if f_stats["failed"] > 0 or f_stats["broken"] > 0:
            badge_cls = "badge-failed"
        elif f_stats["skipped"] > 0:
            badge_cls = "badge-partial"
        else:
            badge_cls = "badge-passed"

        f_total = sum(f_stats.values())
        badge_text = f"{f_stats['passed']}/{f_total} passed"

        content_parts.append('<div class="feature">')
        content_parts.append(
            f'<div class="feature-head">{feature_name} '
            f'<span class="badge {badge_cls}">{badge_text}</span></div>'
        )

        for story_name, tests in sorted(stories.items()):
            content_parts.append('<div class="story">')
            content_parts.append(f'<div class="story-title">Story: {story_name}</div>')
            for t in sorted(tests, key=lambda x: x.get("name", "")):
                content_parts.append(_render_test(t, results_dir))
            content_parts.append("</div>")

        content_parts.append("</div>")

    dur_sec = total_duration_ms / 1000
    dur_str = f"{dur_sec:.2f}s" if dur_sec < 60 else f"{dur_sec / 60:.1f}m"

    html = HTML_TEMPLATE.format(
        title="API Automation Test Report",
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total=stats["total"],
        passed=stats["passed"],
        failed=stats["failed"],
        broken=stats["broken"],
        skipped=stats["skipped"],
        duration=dur_str,
        content="\n".join(content_parts),
    )

    out_path = output_dir / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Report written to: {out_path.resolve()}")
    print(f"Open in browser: file:///{str(out_path.resolve()).replace(os.sep, '/')}")


# ============================================================================
# CLI
# ============================================================================
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    _results = project_root / "reports" / "allure-results"
    _output = project_root / "reports" / "allure-report"

    if len(sys.argv) > 1:
        _results = Path(sys.argv[1])
    if len(sys.argv) > 2:
        _output = Path(sys.argv[2])

    build_report(str(_results), str(_output))
