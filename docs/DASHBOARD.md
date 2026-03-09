# Dashboard Documentation

The monitoring dashboard is a Flask web app running on the miner server at **http://167.71.143.194:9090**.

---

## Architecture

```
Browser
  └── http://167.71.143.194:9090
        └── dashboard/app.py  (Flask, PM2 process: synth-dashboard)
              ├── reads /root/prediction_log.jsonl  (written by synth_integration.py)
              ├── fetches actual prices from yfinance (batched per asset)
              ├── estimates CRPS using Gaussian approximation from p10/p90 paths
              └── queries Bittensor metagraph for on-chain metrics
```

The dashboard is served **from the miner server itself**, not locally. Both the miner (`synth-miner`) and the dashboard (`synth-dashboard`) are managed by PM2 using `miner.official.config.js`.

---

## API Endpoints

### `GET /`
Returns the main HTML dashboard (`dashboard/templates/index.html`). Auto-refreshes every 60 seconds.

---

### `GET /api/status`
Returns PM2 process status and basic server info.

**Response:**
```json
{
  "pm2": { "status": "online", "uptime": "12h 5m", ... },
  "requests_24h": 400,
  "requests_1h": 18,
  "server_time": "2026-03-06T12:00:00Z"
}
```

---

### `GET /api/predictions`
Returns recent predictions with CRPS-aligned accuracy statistics.

**Behaviour:**
- Loads the last `MAX_RECORDS_STATS = 2000` records for computing stats
- Returns the last 50 records (reversed, newest first) for the table display
- Scoring is computed only for `SCORING_ASSETS = {"BTC", "ETH", "SOL"}`
- Uses batched yfinance downloads to avoid rate limiting
- Stats include estimated CRPS, calibration, spread, MAE, direction accuracy
- Per-asset CRPS breakdown included
- Results are cached for `STATS_CACHE_TTL = 300` seconds

**Response:**
```json
{
  "records": [ ... ],
  "stats": {
    "total_logged": 1234,
    "scored_count": 150,
    "validator_aligned_crps": 38.5,
    "per_interval_crps": { "5m": 8.2, "30m": 9.1, "3h": 10.3, "24h": 10.9 },
    "estimated_crps": 45.20,
    "estimated_crps_pct": 0.0523,
    "calibration_pct": 72.5,
    "avg_spread_pct": 2.14,
    "avg_mae_pct": 0.143,
    "direction_accuracy_pct": 86.5,
    "per_asset": {
      "BTC": { "count": 50, "avg_crps": 42.10, "avg_validator_aligned_crps": 40.1, "avg_mae_pct": 0.12, "calibration_pct": 75.0 },
      "ETH": { "count": 50, "avg_crps": 3.20, "avg_validator_aligned_crps": 36.2, "avg_mae_pct": 0.15, "calibration_pct": 70.0 },
      "SOL": { "count": 50, "avg_crps": 0.45, "avg_validator_aligned_crps": 39.0, "avg_mae_pct": 0.18, "calibration_pct": 72.0 }
    },
    "per_asset_yfinance": {
      "BTC": { "count": 50, "calibration_pct": 75.0, "avg_mae_pct": 0.12 },
      "ETH": { "count": 50, "calibration_pct": 70.0, "avg_mae_pct": 0.15 },
      "SOL": { "count": 50, "calibration_pct": 72.0, "avg_mae_pct": 0.18 },
      "XAU": { "count": 45, "calibration_pct": 68.0, "avg_mae_pct": 0.22 },
      "SPYX": { "count": 40, "calibration_pct": 72.5, "avg_mae_pct": 0.18 }
    },
    "assets": ["BTC", "ETH", "SOL", "XAU", "SPYX"]
  }
}
```

**Key metrics explained:**
- `validator_aligned_crps` — **Primary.** Same definition as subnet: CRPS on price change in basis points over 5m, 30m, 3h, 24h; sum of the four interval CRPS values; averaged over scored records. Lower = better. Approximated from mean/p10/p90 paths and yfinance actuals (see [SCORING_AND_METRICS.md](SCORING_AND_METRICS.md)).
- `per_interval_crps` — `{"5m": …, "30m": …, "3h": …, "24h": …}` average CRPS per interval. Use to see which horizon (short vs long) hurts most.
- `per_asset[].avg_validator_aligned_crps` — Validator-aligned CRPS per asset when available.
- `estimated_crps` / `estimated_crps_pct` — Legacy Gaussian CRPS on raw prices at the endpoint (secondary).
- `calibration_pct` — Percentage of actuals in p10–p90 band. Target ~80%.
- `avg_spread_pct` — Average (p90 − p10) / mean at the endpoint.
- `per_asset_yfinance` — Calibration and MAE for **all** assets (BTC, ETH, SOL, XAU, SPYX, NVDAX, TSLAX, AAPLX, GOOGLX) using Yahoo Finance actuals. **Not validator-comparable** for XAU and tokenised equities; use for internal comparison only. Each key has `count`, `calibration_pct`, `avg_mae_pct`.

---

### `GET /api/charts`
Returns per-asset chart data: the last N predictions with per-prediction CRPS/calibration metrics, plus 48h of actual price history.

**Behaviour:**
- Loads up to 500 recent records, keeps up to 5 predictions per asset within 48h
- Downloads 48h of 5-minute bars from yfinance per asset (one call per asset)
- For each prediction, computes CRPS at every time step where actual data is available
- Prediction paths are downsampled to <=120 points for payload efficiency
- Cached for `CHART_CACHE_TTL = 300` seconds

**Response:**
```json
{
  "BTC": {
    "predictions": [
      {
        "start_time": "2026-03-06T12:00:00+00:00",
        "end_time": "2026-03-07T12:00:00+00:00",
        "predicted": [ {"t": "...", "price": 68000.00}, ... ],
        "p10": [ ... ],
        "p90": [ ... ],
        "crps_estimate": 45.20,
        "crps_pct": 0.0665,
        "calibration_pct": 72.0,
        "spread_pct": 2.14,
        "mae_pct": 0.12,
        "window_complete": true,
        "scored_steps": 200,
        "logged_at": "2026-03-06T12:00:01"
      },
      ...
    ],
    "actual_48h": [
      {"t": "2026-03-04T12:00:00+00:00", "price": 67800.00},
      ...
    ]
  },
  "ETH": { ... },
  ...
}
```

---

### `GET /api/chain`
Returns on-chain metagraph metrics for UID 255 on subnet 50.

**Behaviour:**
- Queries `bt.Subtensor('finney').metagraph(50)` on demand
- Cached for `CHAIN_CACHE_TTL = 600` seconds
- If query fails, returns `{"error": "..."}` with a descriptive message

**Response:**
```json
{
  "uid": 255,
  "netuid": 50,
  "active": true,
  "incentive": 0.0,
  "emission": 0.0,
  "consensus": 0.0,
  "dividends": 0.0,
  "validator_trust": 0.0,
  "stake": 94.64,
  "pruning_score": 0.0,
  "fetched_at": "2026-03-08T10:00:00+00:00",
  "error": null
}
```

> **Bittensor 10.x note**: Uses `bt.Subtensor` (capital S). Attributes used: `mg.I`, `mg.E`, `mg.C`, `mg.D`, `mg.Tv`, `mg.S`, `mg.pruning_score`, `mg.active`.

---

### `GET /api/diagnostics`
Returns an actionable diagnosis for model improvement: calibration status, worst-performing asset, suggested focus, and a list of recommended actions. Uses the same stats as `/api/predictions` (cached).

**Response:**
```json
{
  "calibration_ok": false,
  "worst_asset": "BTC",
  "worst_interval": "24h",
  "suggested_focus": "widen_bands",
  "actions": [
    "Calibration 62.0% is below target (~80%). Actuals often outside p10–p90 band — model is overconfident.",
    "Widen uncertainty: increase volatility (e.g. FALLBACK_SIGMA in synth_integration.py) or scale up spread.",
    "Focus on improving 24h horizon (highest CRPS in per-interval breakdown).",
    "Worst calibration for BTC (58%). Consider asset-specific sigma."
  ],
  "summary": "Calibration low (widen bands)",
  "stats_snapshot": {
    "scored_count": 150,
    "validator_aligned_crps": 38.5,
    "per_interval_crps": { "5m": 8.2, "30m": 9.1, "3h": 10.3, "24h": 10.9 },
    "calibration_pct": 62.0,
    "estimated_crps": 45.2,
    "avg_spread_pct": 2.14,
    "per_asset": { "BTC": { "avg_crps": 50.1, "avg_validator_aligned_crps": 40.1, "calibration_pct": 58, "count": 50 }, ... }
  }
}
```

**Fields:**
- `worst_interval` — Which of 5m / 30m / 3h / 24h has the highest CRPS in `per_interval_crps`; used to suggest horizon-specific tuning.
- Diagnostics use **validator-aligned CRPS** (and per-interval breakdown) when available; actions may include "Focus on improving {worst_interval} horizon".

**`suggested_focus` values:** `widen_bands` (overconfident), `tighten_bands` (underconfident), `per_asset_tuning` (one asset much worse), `check_volatility`, `insufficient_data`.

---

### `GET /api/debug-scoring` *(temporary)*
Returns the last 30 scored records with raw MAE values for diagnosis.

---

## Key Configuration Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MINER_UID` | `255` | Our UID on subnet 50 |
| `NETUID` | `50` | Synth subnet ID |
| `SCORING_ASSETS` | `{"BTC", "ETH", "SOL"}` | Assets with oracle-reliable scoring |
| `MAX_RECORDS` | `200` | Table row limit |
| `MAX_RECORDS_STATS` | `2000` | Records scanned for stat computation |
| `CHART_CACHE_TTL` | `300s` | Chart data cache |
| `STATS_CACHE_TTL` | `300s` | Prediction stats cache |
| `CHAIN_CACHE_TTL` | `600s` | Metagraph cache |
| `MAX_PREDS_PER_ASSET` | `5` | Predictions shown per asset in charts |

---

## CRPS estimation and validator alignment

Validators score **CRPS on price change in basis points** over **four intervals** (5m, 30m, 3h, 24h) and sum them (see [SCORING_AND_METRICS.md](SCORING_AND_METRICS.md)). The dashboard computes the **same quantity** (validator-aligned CRPS) as the primary metric.

**Validator-aligned CRPS (dashboard):**
1. For each scored record, get actual prices at t₀, t+5m, t+30m, t+3h, t+24h from yfinance.
2. Compute actual bp changes: `(P_k - P_0) / P_0 * 10000` for each interval.
3. From mean/p10/p90 paths, approximate mean and sigma of *bp change* per interval; use Gaussian CRPS in bp space: same formula as below with `z = (actual_bp - mean_bp) / sigma_bp`.
4. Sum the four interval CRPS values → one validator-aligned CRPS per record; average over records and expose `validator_aligned_crps` and `per_interval_crps`.

**Legacy (raw-price) CRPS** (still in stats as `estimated_crps`):
1. At each time step, fit a Gaussian: `mu = mean_path[i]`, `sigma = (p90_path[i] - p10_path[i]) / 2.56`
2. Closed-form Gaussian CRPS: `sigma * [z*(2*Phi(z)-1) + 2*phi(z) - 1/sqrt(pi)]` where `z = (actual - mu) / sigma`
3. Average across scored time steps

Both are **approximations** (we only have mean/p10/p90, not the full 1000 paths). Validator-aligned CRPS is the one that matches subnet scoring.

---

## Known Issues and Design Decisions

### yfinance rate limiting
Sequential yfinance calls (one per prediction record) cause rate limiting very quickly. The `_batch_score()` helper downloads one large block of historical data per asset per scoring pass, then looks up each record within that block.

### Oracle mismatch for non-crypto assets
XAU, SPYX, NVDAX, TSLAX, AAPLX, GOOGLX — the subnet uses a different oracle than Yahoo Finance for these. Dashboard scoring for these assets would be misleading. The `SCORING_ASSETS` constant restricts scoring to BTC/ETH/SOL only.

### Timezone handling
All datetimes must be timezone-aware when compared. Records from `prediction_log.jsonl` have naive UTC timestamps (`logged_at` field). The code explicitly applies UTC timezone when parsing these.

### Alpha Stake vs TAO
`mg.S[uid]` returns alpha tokens staked in the subnet (~94.64 ש). This is **not raw TAO**. The dashboard displays it as "Alpha Stake (ש)" to avoid confusion.

---

## Restarting the Dashboard

```bash
ssh root@167.71.143.194
pm2 restart synth-dashboard
pm2 logs synth-dashboard --lines 20 --nostream
```

The dashboard starts on port 9090, as defined in `miner.official.config.js`.

---

## Frontend

The frontend is a single HTML file (`dashboard/templates/index.html`) using:
- **Chart.js 4** + `chartjs-adapter-date-fns` for all charts
- Vanilla JavaScript (no framework)
- Auto-refresh every 60s for status/predictions/logs, 5 min for charts, 10 min for chain

### Dashboard Sections (top to bottom)

1. **Status Bar** — miner status, requests, memory, restarts (from `/api/status`)
2. **On-Chain Metrics** — incentive, emission, validator trust, etc. (from `/api/chain`)
3. **How validators score** — Short panel: CRPS on bp over 5m/30m/3h/24h; prompt score = sum; caveat (yfinance vs Pyth; BTC/ETH/SOL comparable).
4. **Model Performance** — Validator CRPS (primary), calibration, spread, MAE, scored count; per-interval CRPS row (5m, 30m, 3h, 24h); per-asset breakdown (BTC/ETH/SOL); **All assets (yfinance only)** — calibration and MAE for XAU and tokenised equities with caveat (from `/api/predictions`)
5. **Model diagnosis** — summary, suggested focus, worst_interval (if set), and actionable bullets (from `/api/diagnostics`)
6. **CRPS Trend** — time-series chart of CRPS per asset over last 48h (from `/api/charts`)
7. **Price Charts** — 3-column grid, each chart shows 48h actual price + up to 3 overlaid predictions with p10-p90 bands (from `/api/charts`)
8. **Prediction Diagnostics** — per-prediction table: CRPS, calibration, spread, MAE, scored steps, status (from `/api/charts`)
9. **Recent Predictions** — raw prediction records table (from `/api/predictions`)
10. **Live Miner Log** — PM2 stdout log (from `/api/logs`)
