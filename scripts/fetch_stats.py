"""Fetch and print current dashboard stats from the local API."""
import urllib.request, json
d = json.loads(urllib.request.urlopen("http://localhost:9090/api/predictions").read())
s = d.get("stats", {})
print(f"scored_count (48h):     {s.get('scored_count')}")
print(f"validator_aligned_crps: {s.get('validator_aligned_crps')}")
print(f"calibration_pct:        {s.get('calibration_pct')}")
print(f"avg_spread_pct:         {s.get('avg_spread_pct')}")
print(f"per_interval_crps:      {s.get('per_interval_crps')}")
print()
print("Per asset (BTC/ETH/SOL):")
for k, v in s.get("per_asset", {}).items():
    print(f"  {k:6s}  CRPS={v.get('avg_validator_aligned_crps')}  cal={v.get('calibration_pct')}%  n={v.get('count')}")
print()
print("Non-crypto (yfinance only):")
for k, v in s.get("per_asset_yfinance", {}).items():
    print(f"  {k:8s}  cal={v.get('calibration_pct')}%  MAE={v.get('avg_mae_pct')}%  n={v.get('count')}")
