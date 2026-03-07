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
  "pm2_processes": [...],
  "server_time": "2026-03-06T12:00:00"
}
```

---

### `GET /api/predictions`
Returns recent predictions with accuracy statistics.

**Behaviour:**
- Loads the last `MAX_RECORDS_STATS = 2000` records from the log for computing stats
- Returns the last `MAX_RECORDS = 200` records for the table display
- Scoring (MAE) is computed only for `SCORING_ASSETS = {"BTC", "ETH", "SOL"}`
- Uses batched yfinance downloads to avoid rate limiting
- Results are cached in memory for `STATS_CACHE_TTL = 300` seconds

**Response:**
```json
{
  "recent": [...],
  "stats": {
    "BTC": {"count": 12, "avg_mae_pct": 0.42, "avg_mae_abs": 285.00},
    "ETH": {...},
    "SOL": {...}
  },
  "total_predictions": 1234
}
```

**Each record in `recent`:**
```json
{
  "logged_at": "2026-03-06T12:00:01",
  "asset": "BTC",
  "start_time": "2026-03-06T12:00:00+00:00",
  "end_time": "2026-03-06T13:00:00+00:00",
  "price_at_request": 68000.00,
  "mean_path": [...],
  "p10_path": [...],
  "p90_path": [...],
  "predicted_end": 68200.00,
  "actual_end": 68150.00,
  "mae_abs": 50.00,
  "mae_pct": 0.073,
  "status": "scored"
}
```

**Record statuses:**
- `"scored"` — window is complete and actual price was retrieved
- `"pending"` — prediction window hasn't ended yet
- `"unresolved"` — window is complete but yfinance returned no data (market closed, etc.)

---

### `GET /api/charts`
Returns 48 hours of predicted vs actual price data per asset for rendering charts.

**Behaviour:**
- For each of the 9 assets, fetches the most recent prediction from the log (within 48h)
- Fetches 48h of 1-hour historical price data from yfinance
- Cached for `CHART_CACHE_TTL = 300` seconds

**Response:**
```json
{
  "BTC": {
    "actual": [
      {"time": "2026-03-04T12:00:00Z", "price": 67800.00},
      ...
    ],
    "predicted_mean": [
      {"time": "2026-03-06T12:00:00+00:00", "price": 68000.00},
      ...
    ],
    "p10": [...],
    "p90": [...]
  },
  "ETH": {...},
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
  "incentive": 0.002792,
  "emission": 0.000414,
  "consensus": 0.0031,
  "dividends": 0.0,
  "validator_trust": 0.0,
  "stake": 94.64,
  "pruning_score": 0.0,
  "axon_serving": true,
  "hotkey": "5FFApaS75bv..."
}
```

> **Bittensor 10.x note**: Uses `bt.Subtensor` (capital S). Attributes used: `mg.I`, `mg.E`, `mg.C`, `mg.D`, `mg.Tv`, `mg.S`, `mg.pruning_score`, `mg.active`, `mg.axons`, `mg.hotkeys`.

---

### `GET /api/debug-scoring` *(temporary)*
Returns the last 20 scored records with raw MAE values for diagnosis. Intended for debugging only — may be removed in future.

---

## Key Configuration Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MINER_UID` | `255` | Our UID on subnet 50 |
| `NETUID` | `50` | Synth subnet ID |
| `SCORING_ASSETS` | `{"BTC", "ETH", "SOL"}` | Assets with oracle-reliable MAE scoring |
| `MAX_RECORDS` | `200` | Table row limit |
| `MAX_RECORDS_STATS` | `2000` | Records scanned for stat computation |
| `CHART_CACHE_TTL` | `300s` | Chart data cache |
| `STATS_CACHE_TTL` | `300s` | Prediction stats cache |
| `CHAIN_CACHE_TTL` | `600s` | Metagraph cache |

---

## Known Issues and Design Decisions

### yfinance rate limiting
Sequential yfinance calls (one per prediction record) cause rate limiting very quickly. The `_batch_score()` helper in `app.py` solves this by downloading one large block of historical data per asset per scoring pass, then looking up each record within that block. Do not revert this to per-record calls.

### Oracle mismatch for non-crypto assets
XAU, SPYX, NVDAX, TSLAX, AAPLX, GOOGLX — the subnet uses a different oracle than Yahoo Finance for these. Dashboard MAE for these assets would be misleading (thousands of percent error). The `SCORING_ASSETS` constant restricts MAE to BTC/ETH/SOL only.

### Timezone handling
All datetimes must be timezone-aware when compared. Records from `prediction_log.jsonl` have naive UTC timestamps (`logged_at` field). The code explicitly applies UTC timezone when parsing these: `dt.replace(tzinfo=timezone.utc)`.

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
- **Chart.js** + `chartjs-adapter-date-fns` for the per-asset price charts
- Vanilla JavaScript (no framework)
- Auto-refresh every 60 seconds via `setInterval`
- Three sections:
  1. **On-Chain Metrics** — refreshed every 10 min from `/api/chain`
  2. **Predictions table** — refreshed every 60s from `/api/predictions`
  3. **Price Charts** — 3x3 grid of per-asset predicted vs actual charts, refreshed every 5 min from `/api/charts`
