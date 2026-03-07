"""
Synth Miner Dashboard — Flask web app served on the miner server.
Access at http://167.71.143.194:9090

Reads /root/prediction_log.jsonl (written by synth_integration.py),
fetches actual prices from Yahoo Finance for completed windows,
and serves a live-updating HTML dashboard.
"""

import json
import os
import subprocess
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
    global _stats_cache, _stats_cache_ts

    now = datetime.now(timezone.utc)

    # Load all records we need
    all_records = load_prediction_log(MAX_RECORDS_STATS)
    total_logged = len(load_prediction_log(limit=99999))

    # Table: 50 most-recent records (reversed so newest first)
    table_records = list(reversed(all_records))[:50]
    enriched_table = enrich_records(table_records)
    assets_seen = list({r["asset"] for r in enriched_table})

    # Stats: use cache if fresh enough (yfinance calls are slow and rate-limited)
    if (
        _stats_cache
        and _stats_cache_ts is not None
        and (now - _stats_cache_ts).total_seconds() < STATS_CACHE_TTL
    ):
        cached_stats = _stats_cache
    else:
        # Only score assets where yfinance prices match the subnet oracle
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

        # Cap at 200 to keep response time reasonable
        stats_sample = completed_scoring[-200:]
        enriched_stats = enrich_records(stats_sample)

        scored = [r for r in enriched_stats if r["scored"] and r["mae_pct"] is not None]
        avg_mae_pct = round(sum(r["mae_pct"] for r in scored) / len(scored), 3) if scored else None
        dir_correct = [r for r in scored if r.get("direction_correct") is True]
        dir_accuracy = round(len(dir_correct) / len(scored) * 100, 1) if scored else None

        cached_stats = {
            "avg_mae_pct": avg_mae_pct,
            "direction_accuracy_pct": dir_accuracy,
            "scored_count": len(scored),
        }
        _stats_cache = cached_stats
        _stats_cache_ts = now

    return jsonify({
        "records": enriched_table,
        "stats": {
            "total_logged": total_logged,
            "avg_mae_pct": cached_stats["avg_mae_pct"],
            "direction_accuracy_pct": cached_stats["direction_accuracy_pct"],
            "scored_count": cached_stats["scored_count"],
            "assets": assets_seen,
        },
    })


@app.route("/api/logs")
def api_logs():
    """Return recent miner PM2 log lines."""
    return jsonify({"lines": tail_pm2_logs(60)})


@app.route("/api/charts")
def api_charts():
    """
    For each asset, return the most recent prediction's mean/p10/p90 paths as
    timestamped series, plus 48 hours of actual price history from yfinance.
    Results are cached for CHART_CACHE_TTL seconds to avoid hammering yfinance.
    """
    global _chart_cache, _chart_cache_ts
    now = datetime.now(timezone.utc)

    if (
        _chart_cache
        and _chart_cache_ts is not None
        and (now - _chart_cache_ts).total_seconds() < CHART_CACHE_TTL
    ):
        return jsonify(_chart_cache)

    cutoff_48h = now - timedelta(hours=48)
    records = load_prediction_log()

    # Find the most recent prediction per asset within the last 48 hours
    latest_per_asset: dict = {}
    for rec in records:
        asset = rec.get("asset")
        if not asset:
            continue
        try:
            logged_at = datetime.fromisoformat(rec.get("logged_at", "").replace("Z", "+00:00"))
            if logged_at.tzinfo is None:
                logged_at = logged_at.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if logged_at < cutoff_48h:
            continue
        existing = latest_per_asset.get(asset)
        if existing is None:
            latest_per_asset[asset] = rec
        else:
            try:
                existing_dt = datetime.fromisoformat(existing.get("logged_at", "").replace("Z", "+00:00"))
                if existing_dt.tzinfo is None:
                    existing_dt = existing_dt.replace(tzinfo=timezone.utc)
                if logged_at > existing_dt:
                    latest_per_asset[asset] = rec
            except Exception:
                pass

    result: dict = {}

    for asset, rec in latest_per_asset.items():
        ticker = ASSET_TICKERS.get(asset)
        if not ticker:
            continue

        start_time_str = rec.get("start_time", "")
        time_increment = rec.get("time_increment", 300)
        mean_path = rec.get("mean_path") or []
        p10_path = rec.get("p10_path") or []
        p90_path = rec.get("p90_path") or []

        if not mean_path or not start_time_str:
            continue

        try:
            start_dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue

        def _to_series(path):
            return [
                {"t": (start_dt + timedelta(seconds=i * time_increment)).isoformat(), "price": round(float(p), 4)}
                for i, p in enumerate(path)
            ]

        predicted = _to_series(mean_path)
        p10_series = _to_series(p10_path)
        p90_series = _to_series(p90_path)

        # Fetch 48 h of 1-hour actual price bars
        actual = []
        try:
            df = yf.download(
                ticker,
                start=cutoff_48h,
                end=now,
                interval="1h",
                progress=False,
                auto_adjust=True,
            )
            if not df.empty:
                close = df["Close"]
                # Handle multi-level columns (newer yfinance versions)
                if hasattr(close, "columns"):
                    close = close.iloc[:, 0]
                for ts, price in close.items():
                    if hasattr(ts, "isoformat"):
                        actual.append({"t": ts.isoformat(), "price": round(float(price), 4)})
        except Exception:
            pass

        result[asset] = {
            "predicted": predicted,
            "p10": p10_series,
            "p90": p90_series,
            "actual": actual,
            "start_time": start_time_str,
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
