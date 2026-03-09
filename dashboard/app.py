"""
Synth Miner Dashboard — Flask web app served on the miner server.
Access at http://167.71.143.194:9090

Reads /root/prediction_log.jsonl (written by synth_integration.py),
fetches actual prices from Yahoo Finance for completed windows,
and serves a live-updating HTML dashboard.
"""

import json
import math
import os
import subprocess
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yfinance as yf
from flask import Flask, jsonify, render_template

app = Flask(__name__)

PREDICTION_LOG = os.environ.get("PREDICTION_LOG_PATH", "/root/prediction_log.jsonl")
MAX_RECORDS = 200        # records shown in the Recent Predictions table
MAX_RECORDS_STATS = 2000 # records scanned when computing accuracy stats

# Simple in-memory cache for /api/charts (yfinance is slow — refresh every 5 min)
_chart_cache: dict = {}
_chart_cache_ts: datetime | None = None
CHART_CACHE_TTL = 300  # seconds

# Cache for the predictions stats (accuracy computation is slow — refresh every 5 min)
_stats_cache: dict = {}
_stats_cache_ts: datetime | None = None
STATS_CACHE_TTL = 300  # seconds

# Cache for /api/chain (metagraph query is slow — refresh every 10 min)
_chain_cache: dict = {}
_chain_cache_ts: datetime | None = None
CHAIN_CACHE_TTL = 600  # seconds

MINER_UID = 255
NETUID = 50

# Yahoo Finance ticker map — mirrors volatility_calculator.py
ASSET_TICKERS = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "XAU": "GC=F",
    "SPYX": "SPY",
    "NVDAX": "NVDA",
    "TSLAX": "TSLA",
    "AAPLX": "AAPL",
    "GOOGLX": "GOOGL",
}

# Only these assets have yfinance prices that reliably match the subnet oracle.
# XAU (GC=F) and tokenised equities use different oracles — exclude from MAE stats
# to avoid misleading numbers.
SCORING_ASSETS = {"BTC", "ETH", "SOL"}

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_prediction_log(limit: int = MAX_RECORDS):
    """Read the last *limit* entries from prediction_log.jsonl."""
    path = Path(PREDICTION_LOG)
    if not path.exists():
        return []
    try:
        lines = path.read_text().strip().splitlines()
        records = []
        for line in lines[-limit:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return records
    except Exception:
        return []


def fetch_actual_price(asset: str, iso_time: str):
    """
    Return the actual market price for *asset* at *iso_time* using yfinance.
    Returns None if the timestamp is in the future or data is unavailable.
    """
    try:
        ticker = ASSET_TICKERS.get(asset)
        if not ticker:
            return None

        target = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if target > now - timedelta(minutes=10):
            return None  # too recent — price not settled yet

        # Download a small window around the target time
        start = target - timedelta(minutes=10)
        end = target + timedelta(minutes=10)
        df = yf.download(ticker, start=start, end=end, interval="5m", progress=False, auto_adjust=True)
        if df.empty:
            return None

        close = df["Close"]
        if hasattr(close, "iloc"):
            return float(close.iloc[-1])
        return None
    except Exception:
        return None


def pm2_status():
    """Return PM2 info for the synth-miner process."""
    try:
        result = subprocess.run(
            ["pm2", "jlist"],
            capture_output=True, text=True, timeout=5
        )
        processes = json.loads(result.stdout)
        for proc in processes:
            if proc.get("name") == "synth-miner":
                pm2 = proc.get("pm2_env", {})
                monit = proc.get("monit", {})
                started_at = pm2.get("pm_uptime")
                uptime_str = "–"
                if started_at:
                    delta = datetime.now() - datetime.fromtimestamp(started_at / 1000)
                    h, rem = divmod(int(delta.total_seconds()), 3600)
                    m = rem // 60
                    uptime_str = f"{h}h {m}m"
                return {
                    "status": pm2.get("status", "unknown"),
                    "uptime": uptime_str,
                    "restarts": pm2.get("restart_time", 0),
                    "memory_mb": round(monit.get("memory", 0) / 1024 / 1024, 1),
                    "cpu_pct": monit.get("cpu", 0),
                    "pid": proc.get("pid"),
                }
    except Exception:
        pass
    return {"status": "unknown", "uptime": "–", "restarts": 0, "memory_mb": 0, "cpu_pct": 0, "pid": None}


def tail_pm2_logs(lines=40):
    """Return recent PM2 out-log lines for the miner."""
    log_path = Path("/root/.pm2/logs/synth-miner-out.log")
    if not log_path.exists():
        return []
    try:
        all_lines = log_path.read_text(errors="replace").splitlines()
        # Strip ANSI colour codes for clean display
        import re
        ansi = re.compile(r"\x1b\[[0-9;]*m")
        clean = [ansi.sub("", l) for l in all_lines[-lines:]]
        return clean
    except Exception:
        return []


def count_recent_requests(hours=24):
    """Count 'Received prediction request' log lines in the last N hours."""
    log_path = Path("/root/.pm2/logs/synth-miner-out.log")
    if not log_path.exists():
        return 0
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        count = 0
        import re
        ts_re = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
        for line in log_path.read_text(errors="replace").splitlines():
            if "Received prediction request" not in line:
                continue
            m = ts_re.search(line)
            if m:
                try:
                    ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                    if ts >= cutoff:
                        count += 1
                except ValueError:
                    pass
        return count
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def compute_mae(mean_path, actual_prices_by_time):
    """
    Given the mean predicted path (list of floats indexed by step) and a dict
    mapping ISO-time strings to actual prices, return the mean absolute error
    in dollars and percentage, and per-step details.
    """
    errors = []
    for i, pred_price in enumerate(mean_path):
        # We don't have direct time here; caller handles matching
        pass
    return None


def _gaussian_crps(mu, sigma, actual):
    """Closed-form CRPS for a Gaussian N(mu, sigma^2) vs observation *actual*."""
    if sigma <= 0:
        return abs(actual - mu)
    z = (actual - mu) / sigma
    phi_z = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    big_phi_z = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return sigma * (z * (2 * big_phi_z - 1) + 2 * phi_z - 1 / math.sqrt(math.pi))


# Validator methodology: CRPS on price change in basis points over 5m, 30m, 3h, 24h.
# Step indices for 5-min increment (steps 0, 1, 6, 36, 288 = t0, 5m, 30m, 3h, 24h).
VALIDATOR_INTERVAL_STEPS = (1, 6, 36, 288)
VALIDATOR_INTERVAL_NAMES = ("5m", "30m", "3h", "24h")


def _crps_bp_interval(mean_bp: float, sigma_bp: float, actual_bp: float) -> float:
    """Gaussian CRPS in basis-point space (same formula as _gaussian_crps)."""
    return _gaussian_crps(mean_bp, sigma_bp, actual_bp)


def _validator_aligned_crps_for_record(rec, close_series, start_dt, time_increment) -> tuple:
    """
    Compute validator-style CRPS for one record: CRPS on bp changes over 5m, 30m, 3h, 24h; sum.
    Returns (validator_aligned_crps, per_interval_crps_dict) or (None, None) if cannot compute.
    """
    mean_path = rec.get("mean_path", [])
    p10_path = rec.get("p10_path", [])
    p90_path = rec.get("p90_path", [])
    n = len(mean_path)
    if n <= VALIDATOR_INTERVAL_STEPS[-1]:
        return None, None
    if not (p10_path and p90_path and len(p10_path) == n and len(p90_path) == n):
        return None, None

    # Actual prices at t0, t+5m, t+30m, t+3h, t+24h
    timestamps = [
        start_dt,
        start_dt + timedelta(seconds=time_increment * 1),
        start_dt + timedelta(seconds=time_increment * 6),
        start_dt + timedelta(seconds=time_increment * 36),
        start_dt + timedelta(seconds=time_increment * 288),
    ]
    actual_prices = []
    for ts in timestamps:
        idx = close_series.index.searchsorted(ts)
        if idx >= len(close_series):
            idx = len(close_series) - 1
        if idx < 0:
            return None, None
        actual_prices.append(float(close_series.iloc[idx]))
    if actual_prices[0] <= 0:
        return None, None

    # Actual bp changes
    actual_bps = [
        (actual_prices[i] - actual_prices[0]) / actual_prices[0] * 10000
        for i in range(1, 5)
    ]

    total_crps = 0.0
    per_interval = {}
    for i, (step_k, name) in enumerate(zip(VALIDATOR_INTERVAL_STEPS, VALIDATOR_INTERVAL_NAMES)):
        p0 = float(mean_path[0])
        pk = float(mean_path[step_k])
        if p0 <= 0:
            continue
        mean_bp = (pk - p0) / p0 * 10000
        # Spread of bp change from p10/p90 paths
        p10_0 = float(p10_path[0])
        p10_k = float(p10_path[step_k])
        p90_0 = float(p90_path[0])
        p90_k = float(p90_path[step_k])
        if p10_0 <= 0 or p90_0 <= 0:
            continue
        p10_bp = (p10_k - p10_0) / p10_0 * 10000
        p90_bp = (p90_k - p90_0) / p90_0 * 10000
        sigma_bp = (p90_bp - p10_bp) / 2.56
        if sigma_bp <= 0:
            sigma_bp = abs(mean_bp) * 0.01 + 1e-6
        crps_k = _crps_bp_interval(mean_bp, sigma_bp, actual_bps[i])
        total_crps += crps_k
        per_interval[name] = round(crps_k, 4)
    return round(total_crps, 4), per_interval


def enrich_records(records):
    """
    For each log record that has a completed forecast window, try to fetch
    the actual price at the start_time and compute MAE of the mean path.
    Adds keys: actual_start_price, mae_pct, scored
    """
    now = datetime.now(timezone.utc)
    enriched = []
    for rec in records:
        rec = dict(rec)  # shallow copy
        rec["scored"] = False
        rec["actual_start_price"] = None
        rec["mae_dollar"] = None
        rec["mae_pct"] = None
        rec["direction_correct"] = None

        start_iso = rec.get("start_time", "")
        end_iso = rec.get("end_time", "")

        try:
            end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
            window_complete = end_dt < now - timedelta(minutes=10)
        except Exception:
            window_complete = False

        if window_complete and rec.get("mean_path") and rec.get("asset") in SCORING_ASSETS:
            # Compare predicted end price vs actual end price (measures forecast quality,
            # not just price calibration at t=0 which is trivially near-zero).
            actual_end = fetch_actual_price(rec["asset"], end_iso)
            if actual_end is not None:
                pred_end = rec["mean_path"][-1]
                rec["actual_start_price"] = round(actual_end, 2)  # reuse field for display
                rec["mae_dollar"] = round(abs(pred_end - actual_end), 2)
                if actual_end > 0:
                    rec["mae_pct"] = round(abs(pred_end - actual_end) / actual_end * 100, 3)

                # Directional accuracy: did we predict up/down from start price correctly?
                price_at_request = rec.get("price_at_request")
                if price_at_request and len(rec["mean_path"]) > 1:
                    pred_direction = rec["mean_path"][-1] > price_at_request
                    actual_direction = actual_end > price_at_request
                    rec["direction_correct"] = pred_direction == actual_direction

                rec["scored"] = True

        enriched.append(rec)
    return enriched


# ---------------------------------------------------------------------------
# Batch scoring helper
# ---------------------------------------------------------------------------

def _batch_score(records, now):
    """
    Score a list of completed prediction records by downloading one price
    history block per asset and looking up each end_time.

    Returns a list of dicts with MAE, direction, CRPS, calibration, and spread.
    """
    by_asset = defaultdict(list)
    for rec in records:
        asset = rec.get("asset")
        if asset in SCORING_ASSETS:
            by_asset[asset].append(rec)

    results = []
    for asset, recs in by_asset.items():
        ticker = ASSET_TICKERS.get(asset)
        if not ticker:
            continue

        end_times = []
        start_times = []
        for rec in recs:
            try:
                et = datetime.fromisoformat(rec["end_time"].replace("Z", "+00:00"))
                if et.tzinfo is None:
                    et = et.replace(tzinfo=timezone.utc)
                end_times.append(et)
                st = datetime.fromisoformat(rec.get("start_time", "").replace("Z", "+00:00"))
                if st.tzinfo is None:
                    st = st.replace(tzinfo=timezone.utc)
                start_times.append(st)
            except Exception:
                pass
        if not end_times:
            continue

        window_start = min(min(end_times), min(start_times)) - timedelta(minutes=15)
        window_end = max(end_times) + timedelta(minutes=15)
        window_start = max(window_start, now - timedelta(hours=50))

        try:
            df = yf.download(
                ticker, start=window_start, end=window_end,
                interval="1m", progress=False, auto_adjust=True,
            )
            if df.empty:
                continue
            close = df["Close"]
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]
        except Exception:
            continue

        for rec in recs:
            try:
                et = datetime.fromisoformat(rec["end_time"].replace("Z", "+00:00"))
                if et.tzinfo is None:
                    et = et.replace(tzinfo=timezone.utc)
                if et > now - timedelta(minutes=10):
                    continue

                idx = close.index.searchsorted(et)
                if idx >= len(close):
                    idx = len(close) - 1
                actual_end = float(close.iloc[idx])

                mean_path = rec.get("mean_path", [])
                p10_path = rec.get("p10_path", [])
                p90_path = rec.get("p90_path", [])
                price_at_req = rec.get("price_at_request")
                if not mean_path or actual_end <= 0:
                    continue

                pred_end = float(mean_path[-1])
                mae_pct = round(abs(pred_end - actual_end) / actual_end * 100, 3)

                direction_correct = None
                if price_at_req:
                    pred_dir = pred_end > float(price_at_req)
                    actual_dir = actual_end > float(price_at_req)
                    direction_correct = pred_dir == actual_dir

                crps_endpoint = None
                in_band = None
                spread_pct = None
                if (p10_path and p90_path
                        and len(p10_path) == len(mean_path)
                        and len(p90_path) == len(mean_path)):
                    p10_end = float(p10_path[-1])
                    p90_end = float(p90_path[-1])
                    sigma = (p90_end - p10_end) / 2.56
                    crps_endpoint = round(_gaussian_crps(pred_end, sigma, actual_end), 4)
                    in_band = p10_end <= actual_end <= p90_end
                    if pred_end > 0:
                        spread_pct = round((p90_end - p10_end) / pred_end * 100, 3)

                validator_aligned_crps = None
                per_interval_crps = None
                try:
                    start_iso = rec.get("start_time", "")
                    time_inc = rec.get("time_increment", 300)
                    start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    val_crps, per_int = _validator_aligned_crps_for_record(
                        rec, close, start_dt, time_inc
                    )
                    validator_aligned_crps = val_crps
                    per_interval_crps = per_int
                except Exception:
                    pass

                results.append({
                    "asset": asset,
                    "mae_pct": mae_pct,
                    "direction_correct": direction_correct,
                    "crps_endpoint": crps_endpoint,
                    "in_band": in_band,
                    "spread_pct": spread_pct,
                    "validator_aligned_crps": validator_aligned_crps,
                    "per_interval_crps": per_interval_crps,
                })
            except Exception:
                pass

    return results


def _batch_score_calibration_only(records, now, assets):
    """
    Score completed records for calibration and MAE only, for any set of assets.
    Uses yfinance actuals. For non-crypto (XAU, equities) these are NOT validator-comparable.
    Returns list of dicts with asset, in_band, mae_pct.
    """
    by_asset = defaultdict(list)
    for rec in records:
        asset = rec.get("asset")
        if asset in assets and asset in ASSET_TICKERS:
            by_asset[asset].append(rec)

    results = []
    for asset, recs in by_asset.items():
        ticker = ASSET_TICKERS.get(asset)
        if not ticker:
            continue

        end_times = []
        start_times = []
        for rec in recs:
            try:
                et = datetime.fromisoformat(rec["end_time"].replace("Z", "+00:00"))
                if et.tzinfo is None:
                    et = et.replace(tzinfo=timezone.utc)
                end_times.append(et)
                st = datetime.fromisoformat(rec.get("start_time", "").replace("Z", "+00:00"))
                if st.tzinfo is None:
                    st = st.replace(tzinfo=timezone.utc)
                start_times.append(st)
            except Exception:
                pass
        if not end_times:
            continue

        window_start = min(min(end_times), min(start_times)) - timedelta(minutes=15)
        window_end = max(end_times) + timedelta(minutes=15)
        window_start = max(window_start, now - timedelta(hours=50))

        try:
            df = yf.download(
                ticker, start=window_start, end=window_end,
                interval="1m", progress=False, auto_adjust=True,
            )
            if df.empty:
                continue
            close = df["Close"]
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]
        except Exception:
            continue

        for rec in recs:
            try:
                et = datetime.fromisoformat(rec["end_time"].replace("Z", "+00:00"))
                if et.tzinfo is None:
                    et = et.replace(tzinfo=timezone.utc)
                if et > now - timedelta(minutes=10):
                    continue

                idx = close.index.searchsorted(et)
                if idx >= len(close):
                    idx = len(close) - 1
                actual_end = float(close.iloc[idx])

                mean_path = rec.get("mean_path", [])
                p10_path = rec.get("p10_path", [])
                p90_path = rec.get("p90_path", [])
                if not mean_path or actual_end <= 0:
                    continue

                pred_end = float(mean_path[-1])
                mae_pct = round(abs(pred_end - actual_end) / actual_end * 100, 3)

                in_band = None
                if (p10_path and p90_path
                        and len(p10_path) == len(mean_path)
                        and len(p90_path) == len(mean_path)):
                    p10_end = float(p10_path[-1])
                    p90_end = float(p90_path[-1])
                    in_band = p10_end <= actual_end <= p90_end

                results.append({
                    "asset": asset,
                    "in_band": in_band,
                    "mae_pct": mae_pct,
                })
            except Exception:
                pass

    return results


def _build_diagnosis(stats: dict) -> dict:
    """
    Build actionable diagnosis from stats. Uses validator-aligned CRPS when available.
    Returns calibration_ok, worst_asset, worst_interval, suggested_focus, and actions list.
    """
    calibration_pct = stats.get("calibration_pct")
    avg_crps = stats.get("estimated_crps")
    avg_validator_crps = stats.get("validator_aligned_crps")
    per_interval_crps = stats.get("per_interval_crps") or {}
    avg_spread_pct = stats.get("avg_spread_pct")
    per_asset = stats.get("per_asset") or {}
    scored_count = stats.get("scored_count") or 0

    calibration_ok = None
    if calibration_pct is not None:
        calibration_ok = 65 <= calibration_pct <= 95

    worst_asset = None
    worst_crps = None
    crps_key = "avg_validator_aligned_crps" if any(pa.get("avg_validator_aligned_crps") is not None for pa in per_asset.values()) else "avg_crps"
    for asset, pa in per_asset.items():
        val = pa.get(crps_key) if crps_key == "avg_validator_aligned_crps" else pa.get("avg_crps")
        if val is not None and pa.get("count", 0) > 0:
            if worst_crps is None or val > worst_crps:
                worst_crps = val
                worst_asset = asset

    worst_interval = None
    if per_interval_crps:
        valid = {k: v for k, v in per_interval_crps.items() if v is not None}
        if valid:
            worst_interval = max(valid, key=valid.get)

    suggested_focus = "insufficient_data"
    actions = []

    if scored_count == 0:
        actions.append("No completed prediction windows yet. Wait for validator requests and for windows to close.")
        return {
            "calibration_ok": None,
            "worst_asset": None,
            "worst_interval": None,
            "suggested_focus": suggested_focus,
            "actions": actions,
            "summary": "Insufficient data",
            "stats_snapshot": {},
        }

    if calibration_pct is not None and calibration_pct < 65:
        suggested_focus = "widen_bands"
        actions.append(
            f"Calibration {calibration_pct:.1f}% is below target (~80%). Actuals often outside p10–p90 band — model is overconfident."
        )
        actions.append(
            "Widen uncertainty: increase volatility (e.g. FALLBACK_SIGMA in synth_integration.py) or scale up spread."
        )
        if worst_asset:
            pa = per_asset.get(worst_asset, {})
            if pa.get("calibration_pct") is not None and pa["calibration_pct"] < 65:
                actions.append(f"Worst calibration for {worst_asset} ({pa['calibration_pct']:.0f}%). Consider asset-specific sigma.")
    elif calibration_pct is not None and calibration_pct > 95:
        suggested_focus = "tighten_bands"
        actions.append(
            f"Calibration {calibration_pct:.1f}% is above target (~80%). Bands are very wide — model is underconfident."
        )
        actions.append(
            "Tighten uncertainty: reduce volatility or scale down spread so p10–p90 is narrower."
        )
    elif worst_asset and len(per_asset) > 1:
        crps_list = [per_asset[a].get(crps_key) or per_asset[a].get("avg_crps") for a in per_asset]
        crps_list = [c for c in crps_list if c is not None]
        if crps_list:
            crps_max = max(crps_list)
            crps_min = min(crps_list)
            if crps_min > 0 and crps_max > 1.5 * crps_min:
                suggested_focus = "per_asset_tuning"
                actions.append(
                    f"{worst_asset} has highest validator-aligned CRPS ({worst_crps:.2f}). Tune volatility or model for {worst_asset}."
                )
                actions.append(
                    "Edit FALLBACK_SIGMA in synth_integration.py or volatility_calculator for that asset."
                )

    if worst_interval:
        actions.append(f"Focus on improving {worst_interval} horizon (highest CRPS in per-interval breakdown).")

    if suggested_focus == "insufficient_data" and (avg_validator_crps is not None or avg_crps is not None or calibration_ok is not None):
        suggested_focus = "check_volatility"
        if calibration_ok:
            actions.append("Calibration is in range. If on-chain CRPS is still poor, check volatility (sigma) and ensemble weights in synth_integration.py.")
        crps_display = avg_validator_crps if avg_validator_crps is not None else avg_crps
        if crps_display is not None:
            actions.append(f"Validator-aligned CRPS (dashboard) is {crps_display:.2f}. Same definition as subnet (bp changes, 5m/30m/3h/24h). Compare with ranking.")

    if not actions:
        actions.append("Keep monitoring. Calibration and per-asset CRPS look acceptable; refine if on-chain rewards don't improve.")

    summary = (
        "Calibration OK" if calibration_ok else
        "Calibration low (widen bands)" if calibration_pct is not None and calibration_pct < 65 else
        "Calibration high (tighten bands)" if calibration_pct is not None and calibration_pct > 95 else
        "Per-asset tuning suggested" if suggested_focus == "per_asset_tuning" else
        "Review volatility and weights"
    )

    return {
        "calibration_ok": calibration_ok,
        "worst_asset": worst_asset,
        "worst_interval": worst_interval,
        "suggested_focus": suggested_focus,
        "actions": actions,
        "summary": summary,
        "stats_snapshot": {
            "scored_count": scored_count,
            "calibration_pct": calibration_pct,
            "estimated_crps": avg_crps,
            "validator_aligned_crps": avg_validator_crps,
            "per_interval_crps": per_interval_crps,
            "avg_spread_pct": avg_spread_pct,
            "per_asset": {a: {"avg_crps": pa.get("avg_crps"), "avg_validator_aligned_crps": pa.get("avg_validator_aligned_crps"), "calibration_pct": pa.get("calibration_pct"), "count": pa.get("count")} for a, pa in per_asset.items()},
        },
    }


def _get_or_compute_stats(all_records: list) -> dict:
    """Return cached stats or compute from all_records and update cache."""
    global _stats_cache, _stats_cache_ts
    now = datetime.now(timezone.utc)
    if (
        _stats_cache
        and _stats_cache_ts is not None
        and (now - _stats_cache_ts).total_seconds() < STATS_CACHE_TTL
    ):
        return _stats_cache

    completed_scoring = []
    completed_scoring_all_assets = []
    for rec in all_records:
        end_iso = rec.get("end_time", "")
        try:
            end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            if end_dt < now - timedelta(minutes=10):
                if rec.get("asset") in SCORING_ASSETS:
                    completed_scoring.append(rec)
                if rec.get("asset") in ASSET_TICKERS:
                    completed_scoring_all_assets.append(rec)
        except Exception:
            pass

    stats_sample = completed_scoring[-200:]
    scored = _batch_score(stats_sample, now)

    # Calibration + MAE for all assets (yfinance only — not validator-comparable for XAU/equities)
    # For BTC/ETH/SOL use the same numbers as per_asset so the two blocks never conflict.
    all_assets_set = set(ASSET_TICKERS.keys())
    per_asset_yfinance = {}
    for a in SCORING_ASSETS:
        if a in per_asset and per_asset[a].get("count", 0) > 0:
            per_asset_yfinance[a] = {
                "count": per_asset[a]["count"],
                "calibration_pct": per_asset[a].get("calibration_pct"),
                "avg_mae_pct": per_asset[a].get("avg_mae_pct"),
            }
    sample_all = completed_scoring_all_assets[-200:]
    scored_all = _batch_score_calibration_only(sample_all, now, all_assets_set - SCORING_ASSETS)
    for asset in all_assets_set - SCORING_ASSETS:
        a_recs = [r for r in scored_all if r["asset"] == asset]
        if not a_recs:
            continue
        a_calib = [r["in_band"] for r in a_recs if r.get("in_band") is not None]
        a_mae = [r["mae_pct"] for r in a_recs]
        per_asset_yfinance[asset] = {
            "count": len(a_recs),
            "calibration_pct": round(
                sum(1 for v in a_calib if v) / len(a_calib) * 100, 1
            ) if a_calib else None,
            "avg_mae_pct": round(sum(a_mae) / len(a_mae), 3) if a_mae else None,
        }
    avg_mae_pct = round(sum(r["mae_pct"] for r in scored) / len(scored), 3) if scored else None
    dir_correct = [r for r in scored if r.get("direction_correct") is True]
    dir_accuracy = round(len(dir_correct) / len(scored) * 100, 1) if scored else None

    crps_vals = [r["crps_endpoint"] for r in scored if r.get("crps_endpoint") is not None]
    avg_crps = round(sum(crps_vals) / len(crps_vals), 2) if crps_vals else None

    val_crps_vals = [r["validator_aligned_crps"] for r in scored if r.get("validator_aligned_crps") is not None]
    avg_validator_aligned_crps = round(sum(val_crps_vals) / len(val_crps_vals), 2) if val_crps_vals else None

    per_interval_sums = defaultdict(float)
    per_interval_counts = defaultdict(int)
    for r in scored:
        pi = r.get("per_interval_crps")
        if pi:
            for k, v in pi.items():
                per_interval_sums[k] += v
                per_interval_counts[k] += 1
    per_interval_crps = {
        k: round(per_interval_sums[k] / per_interval_counts[k], 2) if per_interval_counts[k] else None
        for k in VALIDATOR_INTERVAL_NAMES
    }
    if not any(per_interval_crps.values()):
        per_interval_crps = None

    in_band_vals = [r["in_band"] for r in scored if r.get("in_band") is not None]
    calibration_pct = round(
        sum(1 for v in in_band_vals if v) / len(in_band_vals) * 100, 1
    ) if in_band_vals else None

    spread_vals = [r["spread_pct"] for r in scored if r.get("spread_pct") is not None]
    avg_spread_pct = round(sum(spread_vals) / len(spread_vals), 3) if spread_vals else None

    per_asset = {}
    for a in SCORING_ASSETS:
        a_scored = [r for r in scored if r["asset"] == a]
        a_crps = [r["crps_endpoint"] for r in a_scored if r.get("crps_endpoint") is not None]
        a_val_crps = [r["validator_aligned_crps"] for r in a_scored if r.get("validator_aligned_crps") is not None]
        a_mae = [r["mae_pct"] for r in a_scored]
        a_calib = [r["in_band"] for r in a_scored if r.get("in_band") is not None]
        per_asset[a] = {
            "count": len(a_scored),
            "avg_crps": round(sum(a_crps) / len(a_crps), 2) if a_crps else None,
            "avg_validator_aligned_crps": round(sum(a_val_crps) / len(a_val_crps), 2) if a_val_crps else None,
            "avg_mae_pct": round(sum(a_mae) / len(a_mae), 3) if a_mae else None,
            "calibration_pct": round(
                sum(1 for v in a_calib if v) / len(a_calib) * 100, 1
            ) if a_calib else None,
        }

    cached_stats = {
        "avg_mae_pct": avg_mae_pct,
        "direction_accuracy_pct": dir_accuracy,
        "scored_count": len(scored),
        "estimated_crps": avg_crps,
        "validator_aligned_crps": avg_validator_aligned_crps,
        "per_interval_crps": per_interval_crps,
        "calibration_pct": calibration_pct,
        "avg_spread_pct": avg_spread_pct,
        "per_asset": per_asset,
        "per_asset_yfinance": per_asset_yfinance,
    }
    _stats_cache = cached_stats
    _stats_cache_ts = now
    return cached_stats


# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    """Lightweight endpoint: PM2 health + request counts."""
    return jsonify({
        "pm2": pm2_status(),
        "requests_24h": count_recent_requests(24),
        "requests_1h": count_recent_requests(1),
        "server_time": datetime.utcnow().isoformat() + "Z",
    })


@app.route("/api/predictions")
def api_predictions():
    """Return recent prediction records, enriched with actual prices where available."""
    all_records = load_prediction_log(MAX_RECORDS_STATS)
    total_logged = len(load_prediction_log(limit=99999))
    table_records = list(reversed(all_records))[:50]
    enriched_table = enrich_records(table_records)
    assets_seen = list({r["asset"] for r in enriched_table})
    cached_stats = _get_or_compute_stats(all_records)

    return jsonify({
        "records": enriched_table,
        "stats": {
            "total_logged": total_logged,
            "avg_mae_pct": cached_stats["avg_mae_pct"],
            "direction_accuracy_pct": cached_stats["direction_accuracy_pct"],
            "scored_count": cached_stats["scored_count"],
            "estimated_crps": cached_stats.get("estimated_crps"),
            "validator_aligned_crps": cached_stats.get("validator_aligned_crps"),
            "per_interval_crps": cached_stats.get("per_interval_crps"),
            "calibration_pct": cached_stats.get("calibration_pct"),
            "avg_spread_pct": cached_stats.get("avg_spread_pct"),
            "per_asset": cached_stats.get("per_asset", {}),
            "per_asset_yfinance": cached_stats.get("per_asset_yfinance", {}),
            "assets": assets_seen,
        },
    })


@app.route("/api/diagnostics")
def api_diagnostics():
    """
    Return actionable diagnosis: calibration_ok, worst_asset, suggested_focus,
    and a list of recommended actions. Uses same stats as /api/predictions (cached).
    """
    all_records = load_prediction_log(MAX_RECORDS_STATS)
    stats = _get_or_compute_stats(all_records)
    diagnosis = _build_diagnosis(stats)
    return jsonify(diagnosis)


@app.route("/api/logs")
def api_logs():
    """Return recent miner PM2 log lines."""
    return jsonify({"lines": tail_pm2_logs(60)})


@app.route("/api/charts")
def api_charts():
    """
    For each asset return the last N predictions with per-prediction CRPS,
    calibration, and spread, plus 48h of actual price history for the overview.
    """
    global _chart_cache, _chart_cache_ts
    now = datetime.now(timezone.utc)

    if (
        _chart_cache
        and _chart_cache_ts is not None
        and (now - _chart_cache_ts).total_seconds() < CHART_CACHE_TTL
    ):
        return jsonify(_chart_cache)

    MAX_PREDS_PER_ASSET = 5
    cutoff_48h = now - timedelta(hours=48)
    records = load_prediction_log(500)

    preds_per_asset: dict = defaultdict(list)
    for rec in reversed(records):
        asset = rec.get("asset")
        if not asset:
            continue
        try:
            logged_at = datetime.fromisoformat(
                rec.get("logged_at", "").replace("Z", "+00:00"))
            if logged_at.tzinfo is None:
                logged_at = logged_at.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if logged_at < cutoff_48h:
            continue
        if len(preds_per_asset[asset]) >= MAX_PREDS_PER_ASSET:
            continue
        preds_per_asset[asset].append(rec)

    result: dict = {}

    for asset, recs in preds_per_asset.items():
        ticker = ASSET_TICKERS.get(asset)
        if not ticker:
            continue

        close_series = None
        actual_48h = []
        try:
            df = yf.download(
                ticker, start=cutoff_48h, end=now,
                interval="5m", progress=False, auto_adjust=True,
            )
            if not df.empty:
                close = df["Close"]
                if hasattr(close, "columns"):
                    close = close.iloc[:, 0]
                close_series = close
                for ts, price in close.items():
                    if hasattr(ts, "isoformat"):
                        actual_48h.append({"t": ts.isoformat(), "price": round(float(price), 4)})
        except Exception:
            pass

        predictions = []
        for rec in recs:
            start_time_str = rec.get("start_time", "")
            time_increment = rec.get("time_increment", 300)
            end_time_str = rec.get("end_time", "")
            mean_path = rec.get("mean_path") or []
            p10_path = rec.get("p10_path") or []
            p90_path = rec.get("p90_path") or []

            if not mean_path or not start_time_str:
                continue

            try:
                start_dt = datetime.fromisoformat(
                    start_time_str.replace("Z", "+00:00"))
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue

            num_steps = len(mean_path)
            pred_times = [
                start_dt + timedelta(seconds=i * time_increment)
                for i in range(num_steps)
            ]

            def _ds(path, times):
                """Downsample a path to <=120 points for JSON payload."""
                n = len(path)
                if n <= 120:
                    return [
                        {"t": t.isoformat(), "price": round(float(p), 4)}
                        for t, p in zip(times, path)
                    ]
                step = max(1, n // 120)
                idxs = list(range(0, n, step))
                if n - 1 not in idxs:
                    idxs.append(n - 1)
                return [
                    {"t": times[i].isoformat(), "price": round(float(path[i]), 4)}
                    for i in idxs
                ]

            pred_series = _ds(mean_path, pred_times)
            p10_series = _ds(p10_path, pred_times) if len(p10_path) == num_steps else []
            p90_series = _ds(p90_path, pred_times) if len(p90_path) == num_steps else []

            crps_sum = 0.0
            crps_count = 0
            in_band_hit = 0
            in_band_count = 0
            spread_sum = 0.0
            spread_count = 0

            if close_series is not None and len(close_series) > 0:
                for i, step_time in enumerate(pred_times):
                    if step_time > now - timedelta(minutes=5):
                        break
                    idx = close_series.index.searchsorted(step_time)
                    if idx >= len(close_series):
                        idx = len(close_series) - 1
                    if idx < 0:
                        continue
                    bar_time = close_series.index[idx]
                    try:
                        diff = abs((bar_time.to_pydatetime().replace(
                            tzinfo=timezone.utc) - step_time).total_seconds())
                    except Exception:
                        diff = 9999
                    if diff > 900:
                        continue

                    actual_price = float(close_series.iloc[idx])
                    mu = float(mean_path[i])
                    if (p10_path and p90_path
                            and i < len(p10_path) and i < len(p90_path)):
                        p10_v = float(p10_path[i])
                        p90_v = float(p90_path[i])
                        sigma = (p90_v - p10_v) / 2.56
                        if sigma > 0:
                            crps_sum += _gaussian_crps(mu, sigma, actual_price)
                            crps_count += 1
                        in_band_count += 1
                        if p10_v <= actual_price <= p90_v:
                            in_band_hit += 1
                        if mu > 0:
                            spread_sum += (p90_v - p10_v) / mu * 100
                            spread_count += 1

            crps_est = round(crps_sum / crps_count, 4) if crps_count > 0 else None
            cal_pct = round(in_band_hit / in_band_count * 100, 1) if in_band_count > 0 else None
            sprd_pct = round(spread_sum / spread_count, 3) if spread_count > 0 else None

            mae_pct = None
            if close_series is not None and end_time_str:
                try:
                    end_dt = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                    if end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=timezone.utc)
                    if end_dt < now - timedelta(minutes=5):
                        eidx = close_series.index.searchsorted(end_dt)
                        if eidx >= len(close_series):
                            eidx = len(close_series) - 1
                        ae = float(close_series.iloc[eidx])
                        pe = float(mean_path[-1])
                        if ae > 0:
                            mae_pct = round(abs(pe - ae) / ae * 100, 3)
                except Exception:
                    pass

            window_complete = False
            try:
                if end_time_str:
                    ed = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                    if ed.tzinfo is None:
                        ed = ed.replace(tzinfo=timezone.utc)
                    window_complete = ed < now - timedelta(minutes=10)
            except Exception:
                pass

            predictions.append({
                "start_time": start_time_str,
                "end_time": end_time_str,
                "predicted": pred_series,
                "p10": p10_series,
                "p90": p90_series,
                "crps_estimate": crps_est,
                "calibration_pct": cal_pct,
                "spread_pct": sprd_pct,
                "mae_pct": mae_pct,
                "window_complete": window_complete,
                "scored_steps": crps_count,
                "logged_at": rec.get("logged_at"),
            })

        if predictions or actual_48h:
            result[asset] = {
                "predictions": predictions,
                "actual_48h": actual_48h,
            }

    _chart_cache = result
    _chart_cache_ts = now
    return jsonify(result)


@app.route("/api/debug-scoring")
def api_debug_scoring():
    """Temporary debug: show individual scored record values to diagnose high MAE."""
    now = datetime.now(timezone.utc)
    all_records = load_prediction_log(MAX_RECORDS_STATS)

    completed_scoring = []
    for rec in all_records:
        if rec.get("asset") not in SCORING_ASSETS:
            continue
        end_iso = rec.get("end_time", "")
        try:
            end_dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            if end_dt < now - timedelta(minutes=10):
                completed_scoring.append(rec)
        except Exception:
            pass

    results = []
    for rec in completed_scoring[-30:]:
        asset = rec.get("asset")
        end_iso = rec.get("end_time", "")
        mean_path = rec.get("mean_path", [])
        price_at_req = rec.get("price_at_request")
        pred_end = float(mean_path[-1]) if mean_path else None

        actual_end = fetch_actual_price(asset, end_iso)
        mae_pct = None
        if actual_end is not None and actual_end > 0 and pred_end is not None:
            mae_pct = round(abs(pred_end - actual_end) / actual_end * 100, 4)

        results.append({
            "asset": asset,
            "end_time": end_iso,
            "price_at_req": price_at_req,
            "pred_end": pred_end,
            "actual_end": actual_end,
            "mae_pct": mae_pct,
        })

    scored = [r for r in results if r["mae_pct"] is not None]
    avg = round(sum(r["mae_pct"] for r in scored) / len(scored), 3) if scored else None
    return jsonify({"avg_mae": avg, "scored_count": len(scored), "records": results})


@app.route("/api/chain")
def api_chain():
    """
    Return on-chain metagraph stats for this miner (UID 255, netuid 50).
    Cached for CHAIN_CACHE_TTL seconds — metagraph sync is slow (~10-20s).
    """
    global _chain_cache, _chain_cache_ts
    now = datetime.now(timezone.utc)

    if (
        _chain_cache
        and _chain_cache_ts is not None
        and (now - _chain_cache_ts).total_seconds() < CHAIN_CACHE_TTL
    ):
        return jsonify(_chain_cache)

    try:
        import bittensor as bt  # imported here — not needed for other routes

        subtensor = bt.Subtensor("finney")
        mg = subtensor.metagraph(NETUID)
        uid = MINER_UID

        def _f(arr, idx, decimals=6):
            """Safely index a metagraph array and round."""
            try:
                return round(float(arr[idx]), decimals)
            except Exception:
                return None

        result = {
            "uid": uid,
            "netuid": NETUID,
            "active": bool(mg.active[uid]) if hasattr(mg, "active") else None,
            "stake": _f(mg.S, uid, 4),
            "pruning_score": _f(mg.pruning_score, uid, 6) if hasattr(mg, "pruning_score") else None,
            "validator_trust": _f(mg.Tv, uid, 6) if hasattr(mg, "Tv") else None,
            "consensus": _f(mg.C, uid, 6),
            "incentive": _f(mg.I, uid, 6),
            "emission": _f(mg.E, uid, 6),
            "dividends": _f(mg.D, uid, 6),
            "last_update": int(mg.last_update[uid]) if hasattr(mg, "last_update") else None,
            "fetched_at": now.isoformat(),
            "error": None,
        }
    except Exception as exc:
        result = {
            "uid": MINER_UID,
            "netuid": NETUID,
            "error": str(exc),
            "fetched_at": now.isoformat(),
        }

    _chain_cache = result
    _chain_cache_ts = now
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9090, debug=False)
