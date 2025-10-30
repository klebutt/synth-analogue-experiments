## Synth Miner Deployment Guide (Current Setup)

This guide documents exactly how your miner works today in production, how to verify it, and how to update the models safely.

### High-level architecture
- Process manager: PM2 on the server
- Entrypoint (PM2 script): `/root/synth-subnet/neurons/miner.py`
- Working directory: `/root/synth-subnet`
- Simulation function: `synth.miner.simulations.generate_simulations`
- Delegation: `generate_simulations` delegates to `synth_integration.generate_synth_simulations`
- Integration path: `sys.path.insert(0, '/root/synth-analogue-experiments')` inside `synth-subnet/synth/miner/simulations.py`
- Custom model: `synth_integration.EnsembleGBMWeightedModel`
- Volatility source: `models/baseline/volatility_calculator.get_all_volatilities`
- Price source: `synth.miner.price_simulation.get_asset_price` (Pyth/Hermes)

References: the official miner tutorial explains the miner structure and typical deployment patterns.

### Files that matter
- Server-side repo A: `/root/synth-subnet` (the subnet code the miner runs)
  - `neurons/miner.py`: default miner process (called by PM2)
  - `synth/miner/simulations.py`: delegates to `synth_integration.generate_synth_simulations`
  - `synth/miner/price_simulation.py`: fetches live price
- Server-side repo B: `/root/synth-analogue-experiments` (your custom models)
  - `synth_integration.py`: orchestrates ensemble predictions and uses volatility
  - `models/baseline/volatility_calculator.py`: computes drift/volatility used by the ensemble
  - `models/baseline/*`: baseline components used by the ensemble

Your deployment deliberately keeps subnet code and custom modeling code in separate directories, connected by a path insert in `simulations.py`.

### How to verify what's running (copy/paste)
Run on the server:

1) Confirm PM2 is launching the default miner in the subnet repo
```
pm2 describe miner
```
Expect:
- script path: `/root/synth-subnet/neurons/miner.py`
- exec cwd: `/root/synth-subnet`

2) Confirm Python resolves `synth` from the in-repo path
```
python3 -c "import os, synth; print(os.path.dirname(synth.__file__))"
```
Expect: `/root/synth-subnet/synth`

3) Confirm `generate_simulations` delegates to your integration
```
python3 -c "import inspect, synth.miner.simulations as s; print(inspect.getsource(s.generate_simulations))"
```
Expect to see a call to `generate_synth_simulations(...)` in the try block.

4) Confirm `synth_integration` is imported by `simulations.py`
```
grep -n "synth_integration" /root/synth-subnet/synth/miner/simulations.py || true
```

5) Confirm volatility code is present in your custom repo
```
grep -RniE "get_all_volatil|volatility_calculator" /root/synth-analogue-experiments || true
```

### How the model logic works
- On first use (and every 6 hours per-asset), `EnsembleGBMWeightedModel` calibrates using `get_all_volatilities()` to set drift/volatility.
- Individual models: RandomWalk, GBM, MeanReversion (configurable weights; default GBM-weighted).
- `generate_synth_simulations(...)` consumes a Pyth price for the start price and produces N simulated paths in the subnet-required format.

Key code touchpoints:
- `synth_integration.EnsembleGBMWeightedModel.__init__`: weights and model parameters
- `synth_integration.EnsembleGBMWeightedModel.predict`: calibration + weighted aggregation of base model predictions
- `models/baseline/volatility_calculator.get_all_volatilities`: data source and calculation window for volatility/drift
- `synth.miner.price_simulation.get_asset_price`: live price used for the start value

### Updating or improving models (safe workflow)
Goal: Update your models without breaking the live miner.

1) Make and test changes locally
- Edit files only in `synth-analogue-experiments`:
  - `models/baseline/volatility_calculator.py`
  - `synth_integration.py`
  - Any new models under `models/*`
- Local test (optional):
```
python -c "import synth_integration as s; print('ok', hasattr(s, 'generate_synth_simulations'))"
```

2) Deploy changes to the server
- On server:
```
cd /root/synth-analogue-experiments
git pull
python3 -m pip install -r requirements.txt
```
(Use venv if you prefer: `python3 -m venv .venv && . .venv/bin/activate`.)

3) Verify live integration still resolves and runs
```
python3 -c "import inspect, synth.miner.simulations as s; print(inspect.getsource(s.generate_simulations))"
pm2 logs miner --lines 200
```

4) Optional: Hot-reload
```
pm2 restart miner && pm2 save
```

### Changing the delegation (only if needed)
If you ever decide to stop using `synth_integration`:
- Update `/root/synth-subnet/synth/miner/simulations.py` to remove the import and delegation, or
- Switch PM2 to run `/root/synth-subnet/neurons/custom_miner.py` instead (tutorial-aligned customization pattern).

### Rollback
If a change causes issues:
- Revert your model repo:
```
cd /root/synth-analogue-experiments
git reset --hard <KNOWN_GOOD_COMMIT>
pm2 restart miner && pm2 logs miner --lines 200
```

### Logs and troubleshooting
- Miner logs: `~/.pm2/logs/miner-out.log`, `~/.pm2/logs/miner-error.log`
- Typical checks:
  - Confirm Pyth price fetch works (`synth/m**/price_simulation.py`)
  - Confirm path insertion exists in `synth/miner/simulations.py`
  - Confirm `generate_synth_simulations` callable in `synth_integration`

### Suggested repository hygiene
- Keep subnet code and model code separate (as you do now).
- Avoid editing `synth/` for model logic; prefer your model repo (`synth-analogue-experiments`) + delegation.
- Remove unused duplicates and binaries from your model repo (e.g., top-level `custom_synth_miner.py`, `*.exe`).
- Add `.gitignore` entries: `*.exe`, `__pycache__/`, `.venv/`.

### Appendix: Useful commands
```
pm2 describe miner
pm2 logs miner --lines 200
python3 -c "import os, synth; print(os.path.dirname(synth.__file__))"
python3 -c "import inspect, synth.miner.simulations as s; print(inspect.getsource(s.generate_simulations))"
grep -n "synth_integration" /root/synth-subnet/synth/miner/simulations.py || true
grep -RniE "get_all_volatil|volatility_calculator" /root/synth-analogue-experiments || true
```


