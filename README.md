# Synth Analog Experiments

## Project Overview
This repo is a workspace for developing and testing **analog-inspired AI modules** for [Bittensor’s Synth subnet](https://github.com/opentensor/synth).  
The goal is to ground early technical progress in our long-term vision of **Analog-Inspired AGI**, while also generating income and traction by contributing useful forecasting modules to Synth.

## Why This Project?
- **Long-term vision**: We believe AGI requires more than current machine learning and LLM approaches. Specifically, it needs:
  - Abductive reasoning (Peirce’s logic of discovery).  
  - Handling continuous, time-based data streams.  
  - Parallelism and efficiency (analog-like computation).  
  - Continuous learning and self-organization.  
  - The ability to integrate values and meaning.  
- **Practical short-term**: Synth provides a feasible first testbed. Contributing forecasting models can both:
  - Demonstrate analog-inspired techniques in a live environment.  
  - Generate TAO (Bittensor’s token), funding ongoing development.  

This repo bridges vision and practice.

---

## Stage 2a: First Subnet Engagement (Synth)

### Overarching Objectives
1. **Develop analog-inspired forecasting modules** that can outperform baselines on Synth.  
2. **Validate these methods** in a real subnet environment.  
3. **Earn TAO rewards** to sustain and scale the project.  

### Technical Roadmap (Steps 1–3)

**Step 1: Environment Setup**
- Clone the Synth repo and get a test miner running locally.  
- Ensure local environment can ingest time-series data and submit forecasts.  

**Output:** Working local miner connected to Synth test network.  

---

**Step 2: Baseline Forecasting**
- Implement simple models (e.g., moving average, ARIMA, basic MLP) to establish benchmarks.  
- Document performance and limitations.  

**Output:** Baseline forecast results + comparison notebook.  

---

**Step 3: Analog-Inspired Forecasting Module**
- Prototype analog-inspired approaches:  
  - Continuous-time dynamics (ODE-based models).  
  - Reservoir computing / echo state networks.  
  - Abductive signal interpretation (simple rule-driven anomaly detection + hypothesis generation).  
- Integrate module into Synth miner interface.  
- Compare with baselines.  

**Output:**  
- Analog-inspired model integrated with Synth miner.  
- Experiment results (performance + reward data).  

---

## 🚀 Current Status

### ✅ **Deployed & Running**
- **Miner**: Running on DigitalOcean server (167.71.143.194)
- **UID**: 233 on Synth subnet 50
- **Stake**: 94.64 τ (recently staked +1 TAO)
- **Model**: Ensemble (GBM-weighted) with CRPS ~547.30

### 🚧 **In Progress**
- **Dashboard**: Web interface for monitoring (needs fixing)
- **Data Fetching**: Sequential SSH commands for reliability

### 📊 **Key Metrics**
- **Validator Requests**: 0 (waiting for requests)
- **Wallet Balance**: ~1.1976 τ
- **Miner Status**: Online and running

## 📁 Repo Structure
```
synth-analogue-experiments/
├── custom_synth_miner.py      # Main miner implementation
├── synth_integration.py       # Ensemble model integration
├── miner_api.py              # Dashboard API (needs fixing)
├── miner_dashboard.html      # Web dashboard
├── models/                   # Prediction models
│   ├── baseline/            # Random walk, GBM, mean reversion
│   └── analog/              # Fluid dynamics models
├── miner_monitoring_commands.md  # SSH command reference
├── worklog_2025-10-11_final.md   # Development log
└── synth-subnet/            # Official subnet code
```

## 🔧 Quick Start

### **Check Miner Status**
```bash
ssh root@167.71.143.194 "pm2 status | grep custom-miner"
```

### **View Dashboard**
```bash
python miner_api.py  # Start API
# Open http://localhost:5000
```

### **Monitor Logs**
```bash
ssh root@167.71.143.194 "pm2 logs custom-miner --follow"
```
