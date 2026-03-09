"""
Debug script: investigate why SOL and XAU show 0% calibration.
Run on the server: python3.11 /root/synth-analogue-experiments/scripts/debug_calibration.py
"""
import json
import datetime
import sys
import yfinance as yf

PREDICTION_LOG = "/root/prediction_log.jsonl"
now = datetime.datetime.now(datetime.timezone.utc)

lines = open(PREDICTION_LOG).read().strip().splitlines()
records = [json.loads(l) for l in lines]

def check_asset(asset, ticker):
    completed = []
    for r in records:
        if r.get("asset") != asset:
            continue
        try:
            et = datetime.datetime.fromisoformat(r["end_time"].replace("Z", "+00:00"))
            if (now - et).total_seconds() > 3600:
                completed.append((et, r))
        except Exception:
            pass

    if not completed:
        print(f"\n{asset}: no completed records found")
        return

    completed.sort(key=lambda x: x[0])
    sample = completed[-5:]  # last 5 completed windows
    print(f"\n{asset}: {len(completed)} completed records. Sampling last {len(sample)}:")

    for et, rec in sample:
        mean_path = rec.get("mean_path", [])
        p10_path  = rec.get("p10_path", [])
        p90_path  = rec.get("p90_path", [])
        price_req = rec.get("price_at_request")

        if not mean_path:
            print(f"  {et}: mean_path empty")
            continue

        pred_end = mean_path[-1]
        p10_end  = p10_path[-1] if p10_path else None
        p90_end  = p90_path[-1] if p90_path else None

        # Fetch yfinance actual price
        try:
            df = yf.download(
                ticker,
                start=et - datetime.timedelta(minutes=10),
                end=et + datetime.timedelta(minutes=10),
                interval="1m", progress=False, auto_adjust=True,
            )
            close = df["Close"]
            if hasattr(close, "columns"):
                close = close.iloc[:, 0]
            if close.empty:
                actual = None
            else:
                idx = close.index.searchsorted(et)
                if idx >= len(close):
                    idx = len(close) - 1
                actual = float(close.iloc[idx])
        except Exception as e:
            actual = f"ERROR:{e}"

        in_band = None
        if p10_end is not None and p90_end is not None and isinstance(actual, float):
            in_band = p10_end <= actual <= p90_end

        print(
            f"  end={et.strftime('%m-%d %H:%M')} "
            f"| price_req={price_req:.2f} "
            f"| pred_end={pred_end:.2f} "
            f"| p10={p10_end:.2f} p90={p90_end:.2f} "
            f"| actual={actual if actual is None else f'{actual:.2f}' if isinstance(actual, float) else actual} "
            f"| in_band={in_band}"
        )

print("=== Calibration debug ===")
check_asset("SOL", "SOL-USD")
check_asset("XAU", "GC=F")
check_asset("BTC", "BTC-USD")
