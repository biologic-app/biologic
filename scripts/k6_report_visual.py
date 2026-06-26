#!/usr/bin/env python3
"""k6_report.py — parse a k6 --out json log and produce a self-contained HTML
use-case health report (dark / light theme, sidebar + detail pane, i18n ru/en).

Usage:
    k6 run --out json=results.jsonl script.js
    python3 k6_report.py results.jsonl              # writes results.html
    python3 k6_report.py results.jsonl -o report.html
    python3 k6_report.py results.jsonl --title "Cart API" --base-url http://localhost:8080
"""

import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import re
import sys

# ── cli ──────────────────────────────────────────────────────────────────────


def parse_args():
    p = argparse.ArgumentParser(description="k6 JSON → HTML use-case report")
    p.add_argument(
        "input",
        nargs="+",
        help="one or more k6 --out json log files (NDJSON); multiple inputs "
        "are merged into a single combined report",
    )
    p.add_argument(
        "-o", "--output", default="", help="output HTML path (default: <input>.html)"
    )
    p.add_argument(
        "--title", default="API — Use Case Health", help="report title / project name"
    )
    p.add_argument("--base-url", default="", help="BASE_URL shown in the header")
    return p.parse_args()


# ── ndjson reader ─────────────────────────────────────────────────────────────


def iter_points(path: Path):
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                yield json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"  [warn] line {lineno}: {exc}", file=sys.stderr)


# ── data collection ───────────────────────────────────────────────────────────

STATUS_RE = re.compile(r"→\s*(\d{3})")
EP_RE = re.compile(r"(GET|POST|PATCH|DELETE|PUT)\s+(/[\w/:{}.?*@-]+)", re.IGNORECASE)


def infer_status(name: str) -> str:
    m = STATUS_RE.search(name)
    if m:
        return m.group(1)
    m2 = re.search(r"\b([1-5]\d{2})\b", name)
    if m2:
        return m2.group(1)
    return "ok"


def is_expected_error(status: str) -> bool:
    return status in {"400", "401", "403", "404", "409", "422", "429", "500", "503"}


def percentile(data: list[float], pct: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * pct / 100
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def collect(paths: list[Path]) -> dict:
    # keyed by scenario id
    scenario_checks: dict[str, list[dict]] = defaultdict(list)
    scenario_requests: dict[str, list[dict]] = defaultdict(list)
    scenario_meta: dict[str, dict] = {}

    # global
    thresholds: dict[str, list[str]] = {}
    durations: list[float] = []
    timestamps: list[datetime] = []

    # per-(scenario, url, method) for pairing durations to check rows

    vus_max = 0
    total_data_sent = 0.0
    total_data_received = 0.0
    http_req_count = 0
    iterations = 0

    # temp storage: duration for the latest http_reqs point so we can attach it
    # k6 emits http_req_duration *before* http_reqs for the same request — we
    # collect them per (url, method) and grab them when we process the check.
    pending_dur: dict[tuple, float] = {}  # (url, method) → duration ms

    for path in paths:
      # reset per-file pairing state so durations never bleed across contexts
      pending_dur = {}
      for obj in iter_points(path):
        kind = obj.get("type")
        mname = obj.get("metric", "")
        data = obj.get("data", {})
        tags = data.get("tags", {})
        value = data.get("value")
        ts_raw = data.get("time", "")

        if kind == "Metric":
            ths = data.get("thresholds") or []
            if ths:
                thresholds[mname] = ths
            continue

        if kind != "Point":
            continue

        raw_scenario = tags.get("scenario", "")
        context = tags.get("context", "")
        # namespace the scenario id by context so identical UC ids from
        # different bounded contexts (cart UC1 vs catalog UC1) stay separate
        # cards in a merged report; single-file runs are unaffected.
        scenario = f"{context}|{raw_scenario}" if raw_scenario else ""
        url = tags.get("url", "")
        method = tags.get("method", "GET")
        key = (url, method)

        # timestamp
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw)
                timestamps.append(ts)
            except ValueError:
                pass

        # scenario descriptive tags
        if scenario:
            meta = scenario_meta.setdefault(scenario, {})
            for mk in ("uc", "title", "story", "actor", "context"):
                mv = tags.get(mk)
                if mv and not meta.get(mk):
                    meta[mk] = mv

        if mname == "vus_max" and isinstance(value, (int, float)):
            vus_max = max(vus_max, int(value))

        if mname == "data_sent" and isinstance(value, (int, float)):
            total_data_sent += value

        if mname == "data_received" and isinstance(value, (int, float)):
            total_data_received += value

        if mname == "iterations" and isinstance(value, (int, float)):
            iterations += int(value)

        if mname == "http_req_duration" and isinstance(value, (int, float)):
            durations.append(value)
            pending_dur[key] = value  # store for pairing

        if mname == "http_reqs" and isinstance(value, (int, float)) and value > 0:
            http_req_count += 1
            dur = pending_dur.get(key, 0.0)
            req_info = {
                "status": int(tags.get("status", 0) or 0),
                "expected": tags.get("expected_response", "true") == "true",
                "method": method,
                "name": tags.get("name", url),
                "url": url,
                "scenario": scenario,
                "dur": round(dur),
            }
            if scenario:
                scenario_requests[scenario].append(req_info)

        if mname == "checks":
            check_name = tags.get("check", "")
            passed = bool(value)
            entry = {
                "name": check_name,
                "passed": passed,
                "scenario": scenario,
            }
            if scenario:
                scenario_checks[scenario].append(entry)

    # ── build scenario structures ─────────────────────────────────────────────
    all_scenario_ids = sorted(
        set(list(scenario_checks.keys()) + list(scenario_requests.keys()))
    )

    scenarios = {}
    for sc in all_scenario_ids:
        checks_raw = scenario_checks.get(sc, [])
        reqs = scenario_requests.get(sc, [])

        # build a lookup: check_name → request (match by substring of check name)
        # try to pair each http check with a request of the same name/path
        req_by_name: dict[str, dict] = {}
        for r in reqs:
            req_by_name[r["name"]] = r

        enriched_checks = []
        req_idx = 0  # pointer into reqs for sequential pairing
        for c in checks_raw:
            status = infer_status(c["name"])
            exp = is_expected_error(status)
            # try to find a matching request
            req = req_by_name.get(c["name"])
            if req is None and req_idx < len(reqs):
                req = reqs[req_idx]
                req_idx += 1

            # determine kind
            ep_match = EP_RE.search(c["name"])
            kind = "http" if ep_match or (req and req["status"]) else "assert"

            entry = {
                "name": c["name"],
                "ok": c["passed"],
                "kind": kind,
                "status": int(status) if status.isdigit() else 0,
                "expected": exp,
                "method": req["method"] if req else "",
                "path": _path_from(req["url"] if req else ""),
                "dur": req["dur"] if req else 0,
            }
            enriched_checks.append(entry)

        meta = scenario_meta.get(sc, {})
        ctx = meta.get("context", "")
        uc = meta.get("uc", sc.upper())
        # stable, unique selection id; namespaced by context for merged reports
        uid = re.sub(r"[^a-z0-9]+", "-", f"{ctx}-{uc}".lower()).strip("-")
        scenarios[sc] = {
            "id": uid,
            "context": ctx,
            "uc": uc,
            "title": meta.get("title", _derive_title(sc, enriched_checks)),
            "actor": meta.get("actor", ""),
            "story": meta.get("story", ""),
            "endpoint": _derive_endpoint(enriched_checks),
            "checks": enriched_checks,
            "requests": reqs,
        }

    # ── global latency stats ──────────────────────────────────────────────────
    dur_avg = sum(durations) / len(durations) if durations else 0
    dur_p90 = percentile(durations, 90)
    dur_p95 = percentile(durations, 95)
    dur_p99 = percentile(durations, 99)
    dur_max = max(durations, default=0)
    dur_min = min(durations, default=0)

    # ── histogram (8 buckets) ──────────────────────────────────────────────────
    hist_bins, hist_axis = _make_histogram(durations, bins=8)

    # ── endpoint stats ────────────────────────────────────────────────────────
    ep_stats = _endpoint_stats(scenarios)

    # ── status distribution ───────────────────────────────────────────────────
    all_checks = [c for sc in scenarios.values() for c in sc["checks"]]
    status_ok = sum(1 for c in all_checks if c["ok"] and not c["expected"])
    status_exp = sum(1 for c in all_checks if c["expected"])
    status_fail = sum(1 for c in all_checks if not c["ok"])

    # ── check totals ──────────────────────────────────────────────────────────
    total_checks = len(all_checks)
    passed_checks = sum(1 for c in all_checks if c["ok"])

    # ── thresholds ────────────────────────────────────────────────────────────
    threshold_results = []
    for metric, ths in thresholds.items():
        for th in ths:
            passed_th = True
            actual = ""
            if metric == "checks" and "rate==" in th:
                passed_th = passed_checks == total_checks
                actual = f"{passed_checks / max(total_checks, 1) * 100:.0f}%"
            elif metric == "http_req_duration" and "p(95)<" in th:
                limit = float(re.search(r"<(\d+)", th).group(1))
                passed_th = dur_p95 < limit
                actual = f"{dur_p95:.0f} ms"
            threshold_results.append(
                {
                    "metric": metric,
                    "expr": th,
                    "passed": passed_th,
                    "actual": actual,
                }
            )
    if not threshold_results:
        threshold_results = [
            {
                "metric": "checks",
                "expr": "rate==1.00",
                "passed": passed_checks == total_checks,
                "actual": f"{passed_checks / max(total_checks, 1) * 100:.0f}%",
            },
            {
                "metric": "http_req_duration",
                "expr": "p(95)<2000",
                "passed": dur_p95 < 2000,
                "actual": f"{dur_p95:.0f} ms",
            },
        ]

    # ── run timing ────────────────────────────────────────────────────────────
    run_start = min(timestamps) if timestamps else None
    run_end = max(timestamps) if timestamps else None
    run_secs = (run_end - run_start).total_seconds() if run_start and run_end else 0
    rps = round(http_req_count / run_secs, 1) if run_secs > 0 else 0

    sc_pass = sum(1 for sc in scenarios.values() if all(c["ok"] for c in sc["checks"]))
    sc_total = len(scenarios)
    exp_count = sum(
        1 for sc in scenarios.values() for c in sc["checks"] if c["expected"]
    )
    real_fails = sum(
        1 for sc in scenarios.values() for c in sc["checks"] if not c["ok"]
    )

    return {
        "scenarios": scenarios,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "http_req_count": http_req_count,
        "vus_max": vus_max,
        "iterations": iterations,
        "data_sent_kb": total_data_sent / 1024,
        "data_received_kb": total_data_received / 1024,
        "dur_avg": round(dur_avg),
        "dur_p90": round(dur_p90),
        "dur_p95": round(dur_p95),
        "dur_p99": round(dur_p99),
        "dur_max": round(dur_max),
        "dur_min": round(dur_min),
        "hist_bins": hist_bins,
        "hist_axis": hist_axis,
        "ep_stats": ep_stats,
        "status_ok": status_ok,
        "status_exp": status_exp,
        "status_fail": status_fail,
        "run_secs": run_secs,
        "run_start": run_start,
        "rps": rps,
        "threshold_results": threshold_results,
        "sc_pass": sc_pass,
        "sc_total": sc_total,
        "exp_count": exp_count,
        "real_fails": real_fails,
    }


# ── helpers ────────────────────────────────────────────────────────────────────


def _path_from(url: str) -> str:
    """Extract /path from a full URL, stripping scheme+host."""
    m = re.match(r"https?://[^/]+(/.+)", url)
    if m:
        return m.group(1)
    return url or "/"


def _derive_title(sc_id: str, checks: list[dict]) -> str:
    for c in checks:
        label = c["name"]
        clean = re.sub(r"^uc\d+\s+", "", label, flags=re.IGNORECASE).strip()
        if clean and len(clean) > 6:
            name = re.split(r"[→\-—]", clean)[0].strip()
            if name:
                return name.rstrip(" .,")
    return sc_id.upper()


def _derive_endpoint(checks: list[dict]) -> str:
    for c in checks:
        m = EP_RE.search(c["name"])
        if m:
            return f"{m.group(1).upper()} /api/v1{m.group(2)}"
    return ""


def _make_histogram(
    durations: list[float], bins: int = 8
) -> tuple[list[int], list[str]]:
    if not durations:
        return [0] * bins, ["0"] * (bins + 1)
    _lo, hi = 0.0, max(durations)
    if hi == 0:
        return [0] * bins, ["0"] * (bins + 1)
    width = hi / bins
    counts = [0] * bins
    for d in durations:
        idx = min(int(d / width), bins - 1)
        counts[idx] += 1
    axis = [f"{round(i * width)}" for i in range(bins + 1)]
    axis[-1] += "+"
    return counts, axis


def _endpoint_stats(scenarios: dict) -> list[dict]:
    ep_data: dict[str, list[float]] = defaultdict(list)
    for sc in scenarios.values():
        for r in sc["requests"]:
            path = _path_from(r["url"])
            ep = f"{r['method']} {path}"
            ep_data[ep].append(r["dur"])
    result = []
    for ep, durs in sorted(ep_data.items(), key=lambda x: -sum(x[1]) / len(x[1])):
        avg = round(sum(durs) / len(durs))
        p95 = round(percentile(durs, 95))
        result.append({"ep": ep, "avg": avg, "p95": p95, "n": len(durs)})
    return result


# ── JSON serialisation helpers ────────────────────────────────────────────────


def _js(obj) -> str:
    """Compact JSON for embedding in JS."""
    return json.dumps(obj, ensure_ascii=False)


def _fmt_kb(kb: float) -> str:
    if kb >= 1024:
        return f"{kb / 1024:.1f} MB"
    return f"{round(kb)} KB"


# ── HTML generation ───────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="ru" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title}</title>
<style>
  :root{{
    --sans:system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
    --mono:ui-monospace,'SF Mono','SFMono-Regular',Menlo,Consolas,'Liberation Mono',monospace;
  }}
  html[data-theme="dark"]{{
    --bg:#0d1117; --surface:#161b22; --surface2:#1a2029; --surface3:#21262d;
    --border:#2a313c; --border2:#343b46;
    --text:#e6edf3; --muted:#8b949e; --faint:#6e7681;
    --accent:#4f8cff; --accent-soft:rgba(79,140,255,.14);
    --pass:#3fb950; --pass-soft:rgba(63,185,80,.13);
    --exp:#d29922;  --exp-soft:rgba(210,153,34,.14);
    --fail:#f85149; --fail-soft:rgba(248,81,73,.14);
    --shadow:0 8px 28px rgba(0,0,0,.4);
    --track:#22272f;
  }}
  html[data-theme="light"]{{
    --bg:#f3f5f8; --surface:#ffffff; --surface2:#f7f9fb; --surface3:#eef1f5;
    --border:#e2e6ec; --border2:#d4dae2;
    --text:#1c2128; --muted:#5b6573; --faint:#8a93a0;
    --accent:#2f6fe0; --accent-soft:rgba(47,111,224,.10);
    --pass:#1a7f37; --pass-soft:rgba(26,127,55,.10);
    --exp:#9a6700;  --exp-soft:rgba(154,103,0,.10);
    --fail:#cf222e; --fail-soft:rgba(207,34,46,.10);
    --shadow:0 8px 26px rgba(20,30,50,.12);
    --track:#eaeef3;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  html,body{{height:100%}}
  body{{background:var(--bg);color:var(--text);font-family:var(--sans);font-size:13.5px;line-height:1.5;-webkit-font-smoothing:antialiased}}
  .app{{height:100vh;display:grid;grid-template-rows:auto auto auto 1fr;overflow:hidden}}

  /* appbar */
  .appbar{{display:flex;align-items:center;gap:14px;padding:12px 20px;background:var(--surface);border-bottom:1px solid var(--border)}}
  .logo{{width:30px;height:30px;border-radius:7px;background:var(--accent);display:grid;place-items:center;color:#fff;font-weight:800;font-size:14px;letter-spacing:-.5px;flex:none}}
  .titles .eyebrow{{font-family:var(--mono);font-size:10px;font-weight:600;letter-spacing:.13em;text-transform:uppercase;color:var(--accent)}}
  .titles h1{{font-size:16px;font-weight:650;letter-spacing:-.01em;line-height:1.2}}
  .appbar .meta{{font-family:var(--mono);font-size:11.5px;color:var(--muted);margin-left:6px}}
  .appbar .right{{margin-left:auto;display:flex;align-items:center;gap:8px}}
  .iconbtn{{display:inline-flex;align-items:center;gap:7px;height:32px;padding:0 12px;border:1px solid var(--border2);background:var(--surface2);color:var(--text);border-radius:8px;font-size:12.5px;font-weight:550;cursor:pointer;transition:.12s}}
  .iconbtn:hover{{border-color:var(--accent);color:var(--accent)}}

  /* ribbon */
  .ribbon{{display:flex;align-items:center;gap:18px;padding:8px 20px;background:var(--surface);border-bottom:1px solid var(--border);flex-wrap:wrap}}
  .vp{{font-family:var(--mono);font-weight:800;font-size:12px;letter-spacing:.06em;padding:4px 11px;border-radius:6px}}
  .vp.pass{{background:var(--pass-soft);color:var(--pass);border:1px solid color-mix(in srgb,var(--pass) 35%,transparent)}}
  .vp.fail{{background:var(--fail-soft);color:var(--fail);border:1px solid color-mix(in srgb,var(--fail) 35%,transparent)}}
  .kstats{{display:flex;gap:18px;flex-wrap:wrap}}
  .kstat{{display:flex;align-items:baseline;gap:6px;line-height:1}}
  .kstat .n{{font-family:var(--mono);font-size:15px;font-weight:700}}
  .kstat .l{{font-size:11px;color:var(--muted)}}
  .kstat.g .n{{color:var(--pass)}} .kstat.a .n{{color:var(--exp)}} .kstat.b .n{{color:var(--accent)}}
  .ths{{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}}
  .thchip{{display:flex;align-items:center;gap:7px;font-family:var(--mono);font-size:11px;color:var(--muted);white-space:nowrap;border:1px solid var(--border);background:var(--surface2);padding:4px 10px;border-radius:7px}}
  .thchip b{{color:var(--text);font-weight:600}}
  .dot{{width:7px;height:7px;border-radius:50%;flex:none;background:var(--pass)}}
  .dot.a{{background:var(--exp)}} .dot.r{{background:var(--fail)}}

  /* toolbar */
  .toolbar{{display:flex;align-items:center;gap:10px;padding:9px 20px;background:var(--surface2);border-bottom:1px solid var(--border)}}
  .filters{{display:flex;gap:6px}}
  .fchip{{font-size:12px;font-weight:600;color:var(--muted);background:transparent;border:1px solid var(--border2);padding:5px 12px;border-radius:7px;cursor:pointer;transition:.12s;display:flex;align-items:center;gap:7px}}
  .fchip:hover{{color:var(--text);border-color:var(--border2)}}
  .fchip .c{{font-family:var(--mono);font-size:10.5px;color:var(--faint)}}
  .fchip.on{{color:var(--text);background:var(--accent-soft);border-color:color-mix(in srgb,var(--accent) 45%,transparent)}}
  .fchip.on .c{{color:var(--accent)}}
  .search{{margin-left:6px;display:flex;align-items:center;gap:8px;background:var(--surface);border:1px solid var(--border2);border-radius:8px;padding:0 10px;height:32px;min-width:230px}}
  .search input{{border:none;background:none;outline:none;color:var(--text);font-family:var(--sans);font-size:12.5px;width:100%}}
  .search svg{{flex:none;color:var(--faint)}}
  .toolbar .tright{{margin-left:auto;display:flex;gap:8px}}
  .txtbtn{{font-size:12px;color:var(--muted);background:none;border:none;cursor:pointer;padding:5px 8px;border-radius:6px}}
  .txtbtn:hover{{color:var(--accent);background:var(--accent-soft)}}

  /* body two-pane */
  .body{{display:grid;grid-template-columns:312px 1fr;overflow:hidden;min-height:0}}
  .sidebar{{border-right:1px solid var(--border);background:var(--surface);overflow-y:auto;padding:10px}}
  .detail{{overflow-y:auto;padding:22px 26px 60px}}

  /* tree */
  .tnav{{font-size:13px}}
  .navitem{{display:flex;align-items:center;gap:10px;padding:9px 11px;border-radius:8px;cursor:pointer;color:var(--text);transition:.1s;border:1px solid transparent}}
  .navitem:hover{{background:var(--surface2)}}
  .navitem.sel{{background:var(--accent-soft);border-color:color-mix(in srgb,var(--accent) 35%,transparent)}}
  .navitem.overview{{font-weight:600;margin-bottom:6px}}
  .navitem.overview svg{{color:var(--accent)}}
  .grphead{{display:flex;align-items:center;gap:9px;padding:11px 11px 5px;cursor:pointer;user-select:none}}
  .grphead .gi{{font-size:10px;color:var(--faint);transition:.15s}}
  .grphead.collapsed .gi{{transform:rotate(-90deg)}}
  .grphead .gt{{font-size:10.5px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--muted)}}
  .grphead .gname{{font-size:13px;font-weight:600;color:var(--text);letter-spacing:-.01em}}
  .grphead .gtitle{{font-size:12px;color:var(--faint);font-weight:400}}
  .grphead .gcount{{margin-left:auto;font-family:var(--mono);font-size:10.5px;color:var(--faint)}}
  .grpbody{{overflow:hidden}}
  .grphead.collapsed + .grpbody{{display:none}}
  .navitem.scn{{padding-left:13px}}
  .navitem .uc{{font-family:var(--mono);font-size:10.5px;font-weight:700;color:var(--muted);width:30px;flex:none}}
  .navitem .nm{{flex:1;font-size:12.5px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .navitem .scnt{{font-family:var(--mono);font-size:10px;color:var(--faint);display:flex;gap:6px;align-items:center}}
  .navitem .scnt .e{{color:var(--exp)}}
  .navitem.muted{{opacity:.34}}
  .actorchip{{font-family:var(--mono);font-size:9.5px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;padding:1px 6px;border-radius:5px;background:var(--surface3);color:var(--muted)}}

  /* detail header */
  .dhead{{display:flex;align-items:flex-start;gap:14px;margin-bottom:4px}}
  .dhead .uc{{font-family:var(--mono);font-weight:700;font-size:12px;color:var(--accent);background:var(--accent-soft);padding:4px 9px;border-radius:6px;margin-top:2px;white-space:nowrap}}
  .dhead h2{{font-size:21px;font-weight:650;letter-spacing:-.02em}}
  .dhead .sub{{font-family:var(--mono);font-size:12px;color:var(--muted);margin-top:3px;display:flex;gap:12px;flex-wrap:wrap;align-items:center}}
  .dhead .right{{margin-left:auto;display:flex;gap:8px;align-items:center}}
  .pillcnt{{font-family:var(--mono);font-size:11.5px;font-weight:600;padding:3px 10px;border-radius:6px;border:1px solid transparent}}
  .pillcnt.g{{background:var(--pass-soft);color:var(--pass);border-color:color-mix(in srgb,var(--pass) 30%,transparent)}}
  .pillcnt.a{{background:var(--exp-soft);color:var(--exp);border-color:color-mix(in srgb,var(--exp) 30%,transparent)}}

  /* tabs */
  .dtabs{{display:flex;gap:2px;border-bottom:1px solid var(--border);margin:18px 0 18px}}
  .dtab{{font-size:13px;font-weight:550;color:var(--muted);background:none;border:none;cursor:pointer;padding:10px 14px;border-bottom:2px solid transparent;margin-bottom:-1px;display:flex;align-items:center;gap:7px}}
  .dtab:hover{{color:var(--text)}}
  .dtab.on{{color:var(--text);border-bottom-color:var(--accent)}}
  .dtab .c{{font-family:var(--mono);font-size:10.5px;color:var(--faint)}}

  /* checks list */
  .clist{{display:flex;flex-direction:column;border:1px solid var(--border);border-radius:10px;overflow:hidden}}
  .crow{{border-bottom:1px solid var(--border)}}
  .crow:last-child{{border-bottom:none}}
  .chead{{display:grid;grid-template-columns:26px 1fr auto auto auto;gap:12px;align-items:center;padding:10px 14px;cursor:pointer;background:var(--surface)}}
  .chead.assert{{cursor:default}}
  .crow:hover .chead{{background:var(--surface2)}}
  .ic{{width:18px;height:18px;border-radius:50%;display:grid;place-items:center;font-size:11px;font-weight:800}}
  .ic.g{{background:var(--pass-soft);color:var(--pass)}}
  .ic.a{{background:var(--exp-soft);color:var(--exp)}}
  .ic.r{{background:var(--fail-soft);color:var(--fail)}}
  .cname{{font-size:13px;font-weight:500}}
  .cmethod{{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--muted);border:1px solid var(--border2);border-radius:5px;padding:1px 6px}}
  .cstatus{{font-family:var(--mono);font-size:11px;font-weight:700;padding:2px 9px;border-radius:6px}}
  .cstatus.g{{background:var(--pass-soft);color:var(--pass)}}
  .cstatus.a{{background:var(--exp-soft);color:var(--exp)}}
  .cstatus.r{{background:var(--fail-soft);color:var(--fail)}}
  .cstatus.assert{{background:var(--surface3);color:var(--muted);font-weight:600}}
  .cexpand{{display:none;padding:0 14px 14px 52px;background:var(--surface)}}
  .crow.open .cexpand{{display:block}}
  .crow.open .chead{{background:var(--surface2)}}
  .chev{{color:var(--faint);font-size:11px;transition:.15s;width:12px;text-align:center}}
  .crow.open .chev{{transform:rotate(90deg)}}

  .ddetail{{border:1px solid var(--border);border-radius:9px;overflow:hidden;background:var(--surface2)}}
  .ddrow{{display:flex;border-bottom:1px solid var(--border)}}
  .ddrow:last-child{{border-bottom:none}}
  .ddk{{width:128px;flex:none;padding:8px 12px;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;background:var(--surface)}}
  .ddv{{padding:8px 12px;font-family:var(--mono);font-size:12px;color:var(--text);word-break:break-all}}
  .ddv .tag{{color:var(--exp)}}
  .timing{{display:flex;gap:0;height:10px;border-radius:5px;overflow:hidden;margin-top:6px;background:var(--track)}}
  .timing i{{display:block;height:100%}}
  .timing .b{{background:var(--faint)}} .timing .w{{background:var(--accent)}} .timing .r{{background:var(--pass)}}
  .resp{{font-family:var(--mono);font-size:12px;white-space:pre;color:var(--muted);padding:10px 12px;background:var(--bg);border-radius:0}}
  .resplabel{{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--faint);padding:8px 12px 0}}

  /* overview cards */
  .secttitle{{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:26px 0 12px}}
  .secttitle:first-child{{margin-top:0}}
  .cards{{display:grid;gap:14px}}
  .card{{border:1px solid var(--border);border-radius:12px;background:var(--surface);padding:16px 18px}}
  .grid6{{grid-template-columns:repeat(6,1fr)}}
  .grid2{{grid-template-columns:1fr 1fr}}
  .grid3{{grid-template-columns:1.4fr 1fr 1fr}}
  .kbig .n{{font-family:var(--mono);font-size:26px;font-weight:700;line-height:1}}
  .kbig .l{{font-size:11px;color:var(--muted);margin-top:7px}}
  .kbig.g .n{{color:var(--pass)}} .kbig.a .n{{color:var(--exp)}} .kbig.b .n{{color:var(--accent)}}
  .cardlbl{{font-size:13px;font-weight:600;margin-bottom:2px}}
  .cardcap{{font-family:var(--mono);font-size:10.5px;color:var(--faint);margin-bottom:14px}}

  /* histogram */
  .hist{{display:flex;align-items:flex-end;gap:7px;height:130px}}
  .hist .b{{flex:1;background:linear-gradient(var(--accent),color-mix(in srgb,var(--accent) 55%,transparent));border-radius:4px 4px 0 0;min-height:3px}}
  .hist .b:hover{{background:var(--accent)}}
  .histx{{display:flex;justify-content:space-between;font-family:var(--mono);font-size:10px;color:var(--faint);margin-top:8px}}
  .lstats{{display:flex;gap:0;margin-top:16px;border-top:1px solid var(--border);padding-top:14px}}
  .lstats .s{{flex:1;text-align:center;border-right:1px solid var(--border)}}
  .lstats .s:last-child{{border-right:none}}
  .lstats .s .v{{font-family:var(--mono);font-size:16px;font-weight:700}}
  .lstats .s .k{{font-size:10px;color:var(--muted);margin-top:3px}}

  /* endpoint bars */
  .ebars{{display:flex;flex-direction:column;gap:11px}}
  .ebar{{display:grid;grid-template-columns:1fr;gap:5px}}
  .ebar .top{{display:flex;justify-content:space-between;align-items:baseline;font-size:12px}}
  .ebar .ep{{font-family:var(--mono);font-size:11.5px;color:var(--text)}}
  .ebar .vv{{font-family:var(--mono);font-size:11px;color:var(--muted)}}
  .ebar .vv b{{color:var(--text)}}
  .ebar .track{{height:7px;border-radius:4px;background:var(--track);overflow:hidden}}
  .ebar .fill{{height:100%;background:var(--accent);border-radius:4px}}
  .ebar .fill.slow{{background:var(--exp)}}

  /* donut */
  .donutwrap{{display:flex;align-items:center;gap:20px}}
  .donut{{width:118px;height:118px;border-radius:50%;flex:none;position:relative}}
  .donut::after{{content:"";position:absolute;inset:24px;border-radius:50%;background:var(--surface)}}
  .donut .dc{{position:absolute;inset:0;display:grid;place-items:center;z-index:2;text-align:center}}
  .donut .dc .n{{font-family:var(--mono);font-size:20px;font-weight:700}}
  .donut .dc .l{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}}
  .leg{{display:flex;flex-direction:column;gap:9px;font-size:12.5px}}
  .leg .li{{display:flex;align-items:center;gap:9px}}
  .leg .li .n{{margin-left:auto;font-family:var(--mono);color:var(--muted)}}

  /* perf scenario summary */
  .pmini{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}}
  .pmini .m{{border:1px solid var(--border);border-radius:10px;padding:12px 14px;background:var(--surface)}}
  .pmini .m .v{{font-family:var(--mono);font-size:18px;font-weight:700}}
  .pmini .m .k{{font-size:11px;color:var(--muted);margin-top:4px}}

  /* waterfall */
  .wf{{display:flex;flex-direction:column;gap:3px}}
  .wfhead{{display:grid;grid-template-columns:240px 1fr 64px;gap:12px;font-size:10.5px;color:var(--faint);font-family:var(--mono);padding:0 0 8px;border-bottom:1px solid var(--border);margin-bottom:6px;text-transform:uppercase;letter-spacing:.05em}}
  .wfrow{{display:grid;grid-template-columns:240px 1fr 64px;gap:12px;align-items:center;padding:5px 0;border-bottom:1px solid var(--border);font-size:12px}}
  .wfrow:last-child{{border-bottom:none}}
  .wfname{{display:flex;align-items:center;gap:8px;overflow:hidden}}
  .wfname .mt{{font-family:var(--mono);font-size:9.5px;font-weight:700;color:var(--muted);width:46px;flex:none}}
  .wfname .nm{{font-family:var(--mono);font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .wftrack{{position:relative;height:16px}}
  .wfbar{{position:absolute;top:2px;height:12px;border-radius:3px;background:var(--accent);min-width:3px}}
  .wfbar.exp{{background:var(--exp)}}
  .wfdur{{font-family:var(--mono);font-size:11px;color:var(--muted);text-align:right}}

  .empty{{color:var(--faint);font-size:13px;padding:30px;text-align:center;border:1px dashed var(--border2);border-radius:10px}}

  ::-webkit-scrollbar{{width:11px;height:11px}}
  ::-webkit-scrollbar-thumb{{background:var(--border2);border-radius:6px;border:3px solid var(--surface)}}
  .sidebar::-webkit-scrollbar-thumb{{border-color:var(--surface)}}
</style>
</head>
<body>
<div class="app">
  <header class="appbar">
    <div class="logo">k6</div>
    <div class="titles">
      <div class="eyebrow" id="eyebrow">Use Case Health Report</div>
      <h1 id="runTitle">{project}</h1>
    </div>
    <div class="meta" id="runMeta"></div>
    <div class="right">
      <button class="iconbtn" id="langBtn" title="Language / Язык">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18"/><path d="M12 3a14 14 0 0 0 0 18"/></svg>
        <span id="langLbl">EN</span>
      </button>
      <button class="iconbtn" id="themeBtn" title="Theme">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        <span id="themeLbl">Светлая</span>
      </button>
    </div>
  </header>

  <div class="ribbon">
    <span class="vp" id="verdictPill">PASS</span>
    <div class="kstats" id="kstats"></div>
    <div class="ths" id="thresholds"></div>
  </div>

  <div class="toolbar">
    <div class="filters" id="filters">
      <button class="fchip on" data-f="all"><span class="lab"></span><span class="c" id="cAll">0</span></button>
      <button class="fchip" data-f="fail"><span class="lab"></span><span class="c" id="cFail">0</span></button>
      <button class="fchip" data-f="exp"><span class="lab"></span><span class="c" id="cExp">0</span></button>
      <button class="fchip" data-f="ok"><span class="lab"></span><span class="c" id="cOk">0</span></button>
    </div>
    <div class="search">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
      <input id="searchInput" placeholder="">
    </div>
    <div class="tright">
      <button class="txtbtn" id="expandAll"></button>
      <button class="txtbtn" id="collapseAll"></button>
    </div>
  </div>

  <div class="body">
    <aside class="sidebar"><nav class="tnav" id="tree"></nav></aside>
    <main class="detail" id="detail"></main>
  </div>
</div>

<script>
/* ========== embedded data (generated by k6_report.py) ========== */
const RUN = {run_json};
const SCENARIOS = {scenarios_json};

/* ========== i18n ========== */
let LANG = 'ru';
const T = {{
  ru:{{
    eyebrow:'Отчёт Use Case Health',
    themeLight:'Светлая', themeDark:'Тёмная',
    kScenarios:'сценариев', kChecks:'проверок', kExpected:'ожидаемых 4xx', kRealfails:'реальных фейлов',
    kRequests:'HTTP-запросов', kP95:'p95', kRps:'req/s',
    fAll:'Все', fFail:'Только фейлы', fExp:'Ожидаемые 4xx', fOk:'Успешные',
    search:'Поиск по проверке…', expandAll:'Развернуть всё', collapseAll:'Свернуть всё',
    treeOverview:'Обзор прогона',
    ovTitle:'Обзор прогона', ovDuration:'длительность',
    sectSummary:'Сводка', sectPerf:'Производительность',
    cardLatDist:'Распределение латентности', capLatDist:'http_req_duration · мс',
    cardEndpoints:'Латентность по эндпоинтам', capEndpoints:'среднее · p95 · кол-во запросов',
    cardStatuses:'Статусы ответов', capStatuses:'реальные vs ожидаемые', donutReq:'запросов',
    legOk:'2xx успешные', legExp:'4xx ожидаемые', legFail:'реальные фейлы',
    cardTraffic:'Трафик и нагрузка', capTraffic:'за весь прогон',
    trSent:'отправлено', trRecv:'получено', trIter:'итераций', trVu:'VU макс',
    expedSuffix:'ожид.', statusExp:'ожид.',
    tabChecks:'Проверки', tabPerf:'Производительность', tabTimeline:'Таймлайн',
    emptyChecks:'Нет проверок под текущий фильтр / поиск.',
    ddRequest:'Запрос', ddStatus:'Статус', ddDuration:'Длительность', respBody:'Тело ответа',
    pReq:'запросов', pSum:'сумма',
    cardScnLat:'Латентность запросов сценария', capScnLat:'в порядке выполнения · мс',
    wfReq:'запрос', wfSeq:n=>'0 → '+n+' ms (последовательно)', wfMs:'мс',
    cardTimeline:'Таймлайн запросов сценария', capTimeline:'водопад · ширина = длительность',
  }},
  en:{{
    eyebrow:'Use Case Health Report',
    themeLight:'Light', themeDark:'Dark',
    kScenarios:'scenarios', kChecks:'checks', kExpected:'expected 4xx', kRealfails:'real failures',
    kRequests:'HTTP requests', kP95:'p95', kRps:'req/s',
    fAll:'All', fFail:'Failures only', fExp:'Expected 4xx', fOk:'Passing',
    search:'Search checks…', expandAll:'Expand all', collapseAll:'Collapse all',
    treeOverview:'Run overview',
    ovTitle:'Run overview', ovDuration:'duration',
    sectSummary:'Summary', sectPerf:'Performance',
    cardLatDist:'Latency distribution', capLatDist:'http_req_duration · ms',
    cardEndpoints:'Latency by endpoint', capEndpoints:'average · p95 · request count',
    cardStatuses:'Response statuses', capStatuses:'real vs expected', donutReq:'requests',
    legOk:'2xx passing', legExp:'4xx expected', legFail:'real failures',
    cardTraffic:'Traffic & load', capTraffic:'whole run',
    trSent:'sent', trRecv:'received', trIter:'iterations', trVu:'VU max',
    expedSuffix:'exp.', statusExp:'exp.',
    tabChecks:'Checks', tabPerf:'Performance', tabTimeline:'Timeline',
    emptyChecks:'No checks match the current filter / search.',
    ddRequest:'Request', ddStatus:'Status', ddDuration:'Duration', respBody:'Response body',
    pReq:'requests', pSum:'total',
    cardScnLat:'Scenario request latency', capScnLat:'in execution order · ms',
    wfReq:'request', wfSeq:n=>'0 → '+n+' ms (sequential)', wfMs:'ms',
    cardTimeline:'Scenario request timeline', capTimeline:'waterfall · width = duration',
  }}
}};
const t = (k,...a) => {{ const v=(T[LANG]&&T[LANG][k]!=null)?T[LANG][k]:k; return typeof v==='function'?v(...a):v; }};
function setThemeLbl(){{const cur=document.documentElement.getAttribute('data-theme');$('#themeLbl').textContent=cur==='dark'?t('themeLight'):t('themeDark');}}
function applyStaticI18n(){{
  $('#eyebrow').textContent=t('eyebrow');
  $('#langLbl').textContent=LANG==='ru'?'EN':'RU';
  setThemeLbl();
  const fmap={{all:'fAll',fail:'fFail',exp:'fExp',ok:'fOk'}};
  document.querySelectorAll('#filters .fchip').forEach(b=>b.querySelector('.lab').textContent=t(fmap[b.dataset.f]));
  $('#searchInput').placeholder=t('search');
  $('#expandAll').textContent=t('expandAll');
  $('#collapseAll').textContent=t('collapseAll');
}}

/* ========== helpers ========== */
const $ = (s,r=document) => r.querySelector(s);
const el = (tag,cls,html) => {{ const e=document.createElement(tag); if(cls)e.className=cls; if(html!=null)e.innerHTML=html; return e; }};
const allChecks = () => SCENARIOS.flatMap(s=>s.checks);
const scnById = id => SCENARIOS.find(s=>(s.id||s.uc.toLowerCase())===id);
const okCount = s => s.checks.filter(c=>c.ok).length;
const expCount = s => s.checks.filter(c=>c.expected).length;

/* ========== ribbon ========== */
function paintRibbon(){{
  const all=allChecks();
  const passes=all.filter(c=>c.ok).length, total=all.length;
  const scPass=SCENARIOS.filter(s=>s.checks.every(c=>c.ok)).length;
  const verdict=passes===total&&scPass===SCENARIOS.length?'pass':'fail';
  const vp=$('#verdictPill');
  vp.textContent=verdict.toUpperCase(); vp.className='vp '+verdict;

  const ks=$('#kstats'); ks.innerHTML='';
  const kpis=[
    {{n:scPass+'/'+SCENARIOS.length, k:'kScenarios', c:scPass===SCENARIOS.length?'g':''}},
    {{n:passes+'/'+total,            k:'kChecks',    c:passes===total?'g':''}},
    {{n:all.filter(c=>c.expected).length, k:'kExpected', c:'a'}},
    {{n:all.filter(c=>!c.ok).length,      k:'kRealfails', c:''}},
    {{n:RUN.httpCount,  k:'kRequests', c:''}},
    {{n:RUN.dur.p95+' ms', k:'kP95', c:'b'}},
    {{n:RUN.rps,           k:'kRps', c:'b'}},
  ];
  kpis.forEach(k=>ks.appendChild(el('div','kstat '+(k.c||''),'<span class="n">'+k.n+'</span><span class="l">'+t(k.k)+'</span>')));

  $('#runMeta').textContent='· '+RUN.started+' · '+RUN.duration+' · VU '+RUN.vusMax;

  const th=$('#thresholds'); th.innerHTML='';
  RUN.thresholds.forEach(r=>th.appendChild(el('div','thchip',
    '<span class="dot'+(r.ok?'':' r')+'"></span>'+r.name+' &nbsp;<b>'+(r.ok?'✓ ':'✗ ')+r.actual+'</b>')));

  // filter chips
  $('#cAll').textContent=all.length;
  $('#cFail').textContent=all.filter(c=>!c.ok).length;
  $('#cExp').textContent=all.filter(c=>c.expected).length;
  $('#cOk').textContent=all.filter(c=>c.ok&&!c.expected).length;
}}

/* ========== tree ========== */
let state={{sel:'overview',filter:'all',q:''}};

function passFilter(c){{
  if(state.q&&!c.name.toLowerCase().includes(state.q)) return false;
  if(state.filter==='fail') return !c.ok;
  if(state.filter==='exp') return c.expected;
  if(state.filter==='ok') return c.ok&&!c.expected;
  return true;
}}

function buildTree(){{
  const tree=$('#tree'); tree.innerHTML='';
  const ov=el('div','navitem overview'+(state.sel==='overview'?' sel':''),
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg><span class="nm" style="font-weight:600">'+t('treeOverview')+'</span>');
  ov.onclick=()=>select('overview'); tree.appendChild(ov);

  // merged reports span several contexts → group by context; a single-context
  // run keeps the original per-story grouping.
  const contexts=new Set(SCENARIOS.map(s=>s.context||''));
  const groupKey = contexts.size>1 ? (s=>s.context||'') : (s=>s.story||'');
  const groups={{}};
  SCENARIOS.forEach(s=>{{const g=groupKey(s);(groups[g]||(groups[g]=[])).push(s);}});
  Object.entries(groups).forEach(([gname,scns],i)=>{{
    if(gname){{
      const head=el('div','grphead',
        '<span class="gi">▾</span><span class="gname">'+gname+'</span><span class="gcount">'+scns.length+'</span>');
      const body=el('div','grpbody');
      head.onclick=()=>head.classList.toggle('collapsed');
      scns.forEach(s=>body.appendChild(makeNavItem(s)));
      tree.appendChild(head); tree.appendChild(body);
    }} else {{
      scns.forEach(s=>tree.appendChild(makeNavItem(s)));
    }}
  }});
}}

function makeNavItem(s){{
  const ec=expCount(s), oc=okCount(s);
  const match=s.checks.some(c=>passFilter(c));
  const sid=s.id||s.uc.toLowerCase();
  const item=el('div','navitem scn'+(state.sel===sid?' sel':'')+(match?'':' muted'),
    '<span class="uc">'+s.uc+'</span>'+
    '<span class="nm">'+s.title+'</span>'+
    '<span class="scnt">'+(s.actor?'<span class="actorchip">'+s.actor+'</span>':'')+oc+(ec?' <span class="e">·'+ec+'◆</span>':'')+'</span>');
  item.onclick=()=>select(sid);
  return item;
}}

/* ========== select / render ========== */
function select(id){{
  state.sel=id; buildTree();
  if(id==='overview') renderOverview(); else renderScenario(scnById(id));
  $('#detail').scrollTop=0;
}}

/* ---- overview ---- */
function renderOverview(){{
  const d=$('#detail'); d.innerHTML='';
  const all=allChecks();
  const passes=all.filter(c=>c.ok).length, total=all.length;
  const scPass=SCENARIOS.filter(s=>s.checks.every(c=>c.ok)).length;

  d.appendChild(el('div','dhead',
    '<div><h2>'+t('ovTitle')+'</h2><div class="sub"><span>'+RUN.project+'</span><span>'+RUN.started+'</span><span>'+t('ovDuration')+' '+RUN.duration+'</span></div></div>'));

  // KPI row
  d.appendChild(el('div','secttitle',t('sectSummary')));
  const krow=el('div','cards grid6');
  [
    {{n:scPass+'/'+SCENARIOS.length, l:t('kScenarios'), c:scPass===SCENARIOS.length?'g':''}},
    {{n:passes+'/'+total,            l:t('kChecks'),    c:passes===total?'g':''}},
    {{n:all.filter(c=>c.expected).length, l:t('kExpected'), c:'a'}},
    {{n:all.filter(c=>!c.ok).length,      l:t('kRealfails'), c:''}},
    {{n:RUN.httpCount,  l:t('kRequests'), c:''}},
    {{n:RUN.dur.p95+' ms', l:t('kP95'), c:'b'}},
  ].forEach(k=>krow.appendChild(el('div','card kbig '+(k.c||''),'<div class="n">'+k.n+'</div><div class="l">'+k.l+'</div>')));
  d.appendChild(krow);

  // ── performance section: left col = hist + donut + traffic; right col = endpoints ──
  d.appendChild(el('div','secttitle',t('sectPerf')));
  const mainRow=el('div','cards grid2'); mainRow.style.alignItems='start';

  // ── LEFT COLUMN ──
  const leftCol=el('div',''); leftCol.style.cssText='display:flex;flex-direction:column;gap:14px;';

  // histogram
  const hcard=el('div','card');
  hcard.appendChild(el('div','cardlbl',t('cardLatDist')));
  hcard.appendChild(el('div','cardcap',t('capLatDist')));
  const hmax=Math.max(...RUN.hist);
  const hist=el('div','hist');
  RUN.hist.forEach(v=>{{const b=el('div','b');b.style.height=(hmax?v/hmax*100:0)+'%';hist.appendChild(b);}});
  hcard.appendChild(hist);
  const hx=el('div','histx'); RUN.histAxis.forEach(a=>hx.appendChild(el('span','',a))); hcard.appendChild(hx);
  const ls=el('div','lstats');
  [['min',RUN.dur.min],['avg',RUN.dur.avg],['p90',RUN.dur.p90],['p95',RUN.dur.p95],['p99',RUN.dur.p99],['max',RUN.dur.max]]
    .forEach(([k,v])=>ls.appendChild(el('div','s','<div class="v">'+v+'</div><div class="k">'+k+' ms</div>')));
  hcard.appendChild(ls);
  leftCol.appendChild(hcard);

  // status donut
  const s=RUN.status, tot=s.ok+s.exp+s.fail;
  const okPct=tot?s.ok/tot*100:0, expPct=tot?s.exp/tot*100:0;
  const scard=el('div','card');
  scard.appendChild(el('div','cardlbl',t('cardStatuses')));
  scard.appendChild(el('div','cardcap',t('capStatuses')));
  const dw=el('div','donutwrap');
  const donut=el('div','donut');
  donut.style.background='conic-gradient(var(--pass) 0 '+okPct+'%, var(--exp) '+okPct+'% '+(okPct+expPct)+'%, var(--fail) '+(okPct+expPct)+'% 100%)';
  donut.appendChild(el('div','dc','<div><div class="n">'+tot+'</div><div class="l">'+t('donutReq')+'</div></div>'));
  dw.appendChild(donut);
  dw.appendChild(el('div','leg',
    '<div class="li"><span class="dot"></span> '+t('legOk')+' <span class="n">'+s.ok+'</span></div>'+
    '<div class="li"><span class="dot a"></span> '+t('legExp')+' <span class="n">'+s.exp+'</span></div>'+
    '<div class="li"><span class="dot r"></span> '+t('legFail')+' <span class="n">'+s.fail+'</span></div>'));
  scard.appendChild(dw);
  leftCol.appendChild(scard);

  // traffic
  const tcard=el('div','card');
  tcard.appendChild(el('div','cardlbl',t('cardTraffic')));
  tcard.appendChild(el('div','cardcap',t('capTraffic')));
  const tg=el('div','pmini'); tg.style.marginBottom='0';
  [[t('trSent'),RUN.traffic.sent],[t('trRecv'),RUN.traffic.recv],[t('trIter'),RUN.traffic.iter],[t('trVu'),RUN.vusMax]]
    .forEach(([k,v])=>tg.appendChild(el('div','m','<div class="v">'+v+'</div><div class="k">'+k+'</div>')));
  tcard.appendChild(tg);
  const thl=el('div','');thl.style.marginTop='14px';
  RUN.thresholds.forEach(r=>thl.appendChild(el('div','',
    '<div style="display:flex;align-items:center;gap:9px;font-family:var(--mono);font-size:11.5px;color:var(--muted);padding:6px 0;border-top:1px solid var(--border)"><span class="dot'+(r.ok?'':' r')+'"></span>'+r.name+' <b style="margin-left:auto;color:var(--text)">'+(r.ok?'✓ ':'✗ ')+r.actual+'</b></div>')));
  tcard.appendChild(thl);
  leftCol.appendChild(tcard);

  mainRow.appendChild(leftCol);

  // ── RIGHT COLUMN: endpoints ──
  const ecard=el('div','card');
  ecard.appendChild(el('div','cardlbl',t('cardEndpoints')));
  ecard.appendChild(el('div','cardcap',t('capEndpoints')));
  const emax=Math.max(...RUN.endpoints.map(e=>e.avg));
  const ebars=el('div','ebars');
  RUN.endpoints.forEach(e=>{{
    ebars.appendChild(el('div','ebar',
      '<div class="top"><span class="ep">'+e.ep+'</span><span class="vv"><b>'+e.avg+'</b> · p95 '+e.p95+' · ×'+e.n+'</span></div>'+
      '<div class="track"><div class="fill'+(e.avg>=250?' slow':'')+'" style="width:'+(emax?e.avg/emax*100:0)+'%"></div></div>'));
  }});
  ecard.appendChild(ebars);
  mainRow.appendChild(ecard);

  d.appendChild(mainRow);
}}

/* ---- scenario ---- */
let curTab='checks';
function renderScenario(s){{
  curTab='checks';
  const d=$('#detail'); d.innerHTML='';
  const ec=expCount(s), oc=okCount(s);
  const head=el('div','dhead',
    '<span class="uc">'+s.uc+'</span>'+
    '<div><h2>'+s.title+'</h2><div class="sub">'+(s.actor?'<span class="actorchip">'+s.actor+'</span>':'')+
    (s.endpoint?'<span>'+s.endpoint+'</span>':'')+'</div></div>'+
    '<div class="right"><span class="pillcnt g">'+oc+'/'+s.checks.length+'</span>'+
    (ec?'<span class="pillcnt a">'+ec+' '+t('expedSuffix')+'</span>':'')+'</div>');
  d.appendChild(head);

  const httpChecks=s.checks.filter(c=>c.kind==='http');
  const tabs=el('div','dtabs');
  const body=el('div',''); body.id='tabBody';
  const mk=(id,label,c)=>{{
    const b=el('button','dtab'+(curTab===id?' on':''),label+(c!=null?' <span class="c">'+c+'</span>':''));
    b.onclick=()=>{{curTab=id;[...tabs.children].forEach(x=>x.classList.remove('on'));b.classList.add('on');paintTab(s,body);}};
    return b;
  }};
  tabs.appendChild(mk('checks',t('tabChecks'),s.checks.length));
  tabs.appendChild(mk('perf',t('tabPerf')));
  tabs.appendChild(mk('timeline',t('tabTimeline'),httpChecks.length));
  d.appendChild(tabs);
  d.appendChild(body);
  paintTab(s,body);
}}

function paintTab(s,body){{
  body.innerHTML='';
  if(curTab==='checks') paintChecks(s,body);
  else if(curTab==='perf') paintPerf(s,body);
  else paintTimeline(s,body);
}}

function paintChecks(s,body){{
  const shown=s.checks.filter(passFilter);
  if(!shown.length){{body.appendChild(el('div','empty',t('emptyChecks')));return;}}
  const list=el('div','clist');
  shown.forEach(c=>{{
    const row=el('div','crow');
    const isHttp=c.kind==='http';
    const icCls=!c.ok?'r':(c.expected?'a':'g');
    const icCh=!c.ok?'✕':(c.expected?'◆':'✓');
    let statusHtml;
    if(isHttp){{
      const cls=!c.ok?'r':(c.expected?'a':'g');
      statusHtml='<span class="cstatus '+cls+'">'+c.status+(c.expected?' '+t('statusExp'):'')+'</span>';
    }} else statusHtml='<span class="cstatus assert">assert</span>';
    const head=el('div','chead'+(isHttp?'':' assert'),
      '<span class="ic '+icCls+'">'+icCh+'</span>'+
      '<span class="cname">'+c.name+'</span>'+
      (isHttp?'<span class="cmethod">'+c.method+'</span>':'<span></span>')+
      statusHtml+
      (isHttp?'<span class="chev">›</span>':'<span style="width:12px"></span>'));
    row.appendChild(head);
    if(isHttp && c.dur){{
      const exp=el('div','cexpand');
      const dd=el('div','ddetail');
      const b=Math.max(1,Math.round(c.dur*.04)), w=Math.round(c.dur*.78), r=c.dur-w-b;
      dd.innerHTML=
        '<div class="ddrow"><div class="ddk">'+t('ddRequest')+'</div><div class="ddv">'+c.method+' '+c.path+'</div></div>'+
        '<div class="ddrow"><div class="ddk">'+t('ddStatus')+'</div><div class="ddv">'+c.status+(c.expected?' · expected_response=false (by design)':'')+'</div></div>'+
        '<div class="ddrow"><div class="ddk">'+t('ddDuration')+'</div><div class="ddv">'+c.dur+' ms<div class="timing"><i class="b" style="width:'+(b/c.dur*100)+'%"></i><i class="w" style="width:'+(w/c.dur*100)+'%"></i><i class="r" style="width:'+(r/c.dur*100)+'%"></i></div><div style="font-size:10px;color:var(--faint);margin-top:4px">blocked '+b+' · waiting '+w+' · receiving '+r+' ms</div></div></div>';
      exp.appendChild(dd);
      row.appendChild(exp);
      head.onclick=()=>row.classList.toggle('open');
    }}
    list.appendChild(row);
  }});
  body.appendChild(list);
}}

function paintPerf(s,body){{
  const h=s.checks.filter(c=>c.kind==='http'&&c.dur>0);
  if(!h.length){{body.appendChild(el('div','empty',t('emptyChecks')));return;}}
  const durs=h.map(c=>c.dur).sort((a,b)=>a-b);
  const avg=Math.round(durs.reduce((a,b)=>a+b,0)/durs.length);
  const p95=durs[Math.min(durs.length-1,Math.floor(durs.length*.95))];
  const total=durs.reduce((a,b)=>a+b,0);
  const mini=el('div','pmini');
  [[t('pReq'),h.length],['avg',avg+' ms'],['p95',p95+' ms'],[t('pSum'),total+' ms']]
    .forEach(([k,v])=>mini.appendChild(el('div','m','<div class="v">'+v+'</div><div class="k">'+k+'</div>')));
  body.appendChild(mini);
  const card=el('div','card');
  card.appendChild(el('div','cardlbl',t('cardScnLat')));
  card.appendChild(el('div','cardcap',t('capScnLat')));
  const mmax=Math.max(...h.map(c=>c.dur));
  const bars=el('div','ebars');
  h.forEach(c=>{{
    bars.appendChild(el('div','ebar',
      '<div class="top"><span class="ep">'+c.method+' '+c.path+'</span><span class="vv"><b>'+c.dur+'</b> ms · '+c.status+'</span></div>'+
      '<div class="track"><div class="fill'+(c.dur>=250?' slow':'')+'" style="width:'+(c.dur/mmax*100)+'%"></div></div>'));
  }});
  card.appendChild(bars);
  body.appendChild(card);
}}

function paintTimeline(s,body){{
  const h=s.checks.filter(c=>c.kind==='http'&&c.dur>0);
  if(!h.length){{body.appendChild(el('div','empty',t('emptyChecks')));return;}}
  const total=h.reduce((a,c)=>a+c.dur,0);
  const wf=el('div','wf');
  wf.appendChild(el('div','wfhead','<span>'+t('wfReq')+'</span><span>'+t('wfSeq',total)+'</span><span style="text-align:right">'+t('wfMs')+'</span>'));
  let acc=0;
  h.forEach(c=>{{
    const left=acc/total*100, width=c.dur/total*100; acc+=c.dur;
    wf.appendChild(el('div','wfrow',
      '<div class="wfname"><span class="mt">'+c.method+'</span><span class="nm">'+c.path+'</span></div>'+
      '<div class="wftrack"><div class="wfbar'+(c.expected?' exp':'')+'" style="left:'+left+'%;width:'+Math.max(width,1.5)+'%"></div></div>'+
      '<div class="wfdur">'+c.dur+'</div>'));
  }});
  const card=el('div','card');
  card.appendChild(el('div','cardlbl',t('cardTimeline')));
  card.appendChild(el('div','cardcap',t('capTimeline')));
  card.appendChild(wf);
  body.appendChild(card);
}}

/* ========== events ========== */
$('#filters').addEventListener('click',e=>{{
  const b=e.target.closest('.fchip'); if(!b)return;
  state.filter=b.dataset.f;
  [...$('#filters').children].forEach(x=>x.classList.toggle('on',x===b));
  buildTree();
  if(state.sel!=='overview') renderScenario(scnById(state.sel));
}});
$('#searchInput').addEventListener('input',e=>{{
  state.q=e.target.value.trim().toLowerCase();
  buildTree();
  if(state.sel!=='overview') renderScenario(scnById(state.sel));
}});
$('#expandAll').onclick=()=>document.querySelectorAll('.crow').forEach(r=>r.classList.add('open'));
$('#collapseAll').onclick=()=>document.querySelectorAll('.crow').forEach(r=>r.classList.remove('open'));
$('#themeBtn').onclick=()=>{{
  const cur=document.documentElement.getAttribute('data-theme');
  const next=cur==='dark'?'light':'dark';
  document.documentElement.setAttribute('data-theme',next);
  setThemeLbl();
  try{{localStorage.setItem('k6theme',next);}}catch(e){{}}
}};
$('#langBtn').onclick=()=>{{
  LANG=LANG==='ru'?'en':'ru';
  try{{localStorage.setItem('k6lang',LANG);}}catch(e){{}}
  applyStaticI18n();
  paintRibbon();
  buildTree();
  if(state.sel==='overview') renderOverview(); else renderScenario(scnById(state.sel));
}};

/* ========== init ========== */
(function init(){{
  try{{const th=localStorage.getItem('k6theme');if(th)document.documentElement.setAttribute('data-theme',th);}}catch(e){{}}
  try{{const lg=localStorage.getItem('k6lang');if(lg==='ru'||lg==='en')LANG=lg;}}catch(e){{}}
  applyStaticI18n();
  paintRibbon();
  buildTree();
  renderOverview();
}})();
</script>
</body>
</html>
"""


def render_html(data: dict, title: str, base_url: str) -> str:
    run_start = data["run_start"]
    run_secs = data["run_secs"]

    ts_str = run_start.strftime("%Y-%m-%d %H:%M") if run_start else "–"
    # duration: round to 1 decimal, show seconds
    duration_str = f"{run_secs / 60:.1f} мин" if run_secs >= 60 else f"{run_secs:.1f} с"

    # build scenarios JSON for JS (ordered list)
    scenarios_list = []
    for sc in data["scenarios"].values():
        scenarios_list.append(
            {
                "id": sc["id"],
                "context": sc["context"],
                "uc": sc["uc"],
                "title": sc["title"],
                "actor": sc["actor"],
                "story": sc["story"],
                "endpoint": sc["endpoint"],
                "checks": [
                    {
                        "name": c["name"],
                        "kind": c["kind"],
                        "ok": c["ok"],
                        "expected": c["expected"],
                        "status": c["status"],
                        "method": c["method"],
                        "path": c["path"],
                        "dur": c["dur"],
                    }
                    for c in sc["checks"]
                ],
            }
        )

    # thresholds for JS
    thresholds_js = [
        {
            "name": f"{th['metric']} {th['expr']}",
            "ok": th["passed"],
            "actual": th["actual"],
        }
        for th in data["threshold_results"]
    ]

    run_json = _js(
        {
            "project": title,
            "started": ts_str + (" UTC" if run_start and run_start.tzinfo else ""),
            "duration": duration_str,
            "vusMax": data["vus_max"],
            "httpCount": data["http_req_count"],
            "rps": data["rps"],
            "thresholds": thresholds_js,
            "dur": {
                "min": data["dur_min"],
                "avg": data["dur_avg"],
                "p90": data["dur_p90"],
                "p95": data["dur_p95"],
                "p99": data["dur_p99"],
                "max": data["dur_max"],
            },
            "hist": data["hist_bins"],
            "histAxis": data["hist_axis"],
            "endpoints": data["ep_stats"],
            "status": {
                "ok": data["status_ok"],
                "exp": data["status_exp"],
                "fail": data["status_fail"],
            },
            "traffic": {
                "sent": _fmt_kb(data["data_sent_kb"]),
                "recv": _fmt_kb(data["data_received_kb"]),
                "iter": data["iterations"] or data["sc_total"],
            },
        }
    )

    return HTML.format(
        page_title=title,
        project=title,
        run_json=run_json,
        scenarios_json=_js(scenarios_list),
    )


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    args = parse_args()
    srcs = [Path(p) for p in args.input]
    missing = [str(p) for p in srcs if not p.exists()]
    if missing:
        sys.exit(f"Error: file(s) not found: {', '.join(missing)}")

    out_path = Path(args.output) if args.output else srcs[0].with_suffix(".html")

    print("Parsing  " + ", ".join(str(p) for p in srcs) + " …")
    data = collect(srcs)

    print(f"Scenarios found : {len(data['scenarios'])}")
    print(f"Checks          : {data['passed_checks']}/{data['total_checks']} passed")
    print(f"HTTP requests   : {data['http_req_count']}")
    print(f"p95 duration    : {data['dur_p95']} ms")
    print(f"Scenarios pass  : {data['sc_pass']}/{data['sc_total']}")
    print(f"Expected errors : {data['exp_count']}")
    print(f"Real failures   : {data['real_fails']}")

    html = render_html(data, title=args.title, base_url=args.base_url)
    out_path.write_text(html, encoding="utf-8")
    print(f"Report written  → {out_path}")


if __name__ == "__main__":
    main()
