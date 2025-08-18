# Synth Analog Experiments

## Overview

This repository contains experiments with analog-inspired forecasting modules for Bittensor's Synth subnet. Our goal is to bridge long-term analog-inspired AGI research with practical contributions to the Synth network, earning TAO while advancing the field.

## What is This Project?

**Synth Subnet**: A decentralized network where participants compete to provide accurate price predictions and synthetic data. The network rewards participants based on CRPS (Continuous Ranked Probability Score) - a statistical measure of prediction accuracy.

**Analog-Inspired Models**: We're exploring forecasting approaches inspired by analog computing principles - using continuous, fluid-like mathematical relationships rather than discrete digital computations.

## Project Structure

```
synth-analogue-experiments/
├── notebooks/          # Jupyter notebooks for experiments and analysis
├── models/            # Model implementations (baseline + analog-inspired)
├── tests/             # Unit tests and validation
├── docs/              # Documentation and research notes
├── scripts/           # Utility scripts and automation
└── requirements.txt   # Python dependencies
```

## Getting Started

### Prerequisites
- Python 3.8+
- Basic understanding of Python and statistics
- Interest in forecasting and machine learning

### Installation
```bash
git clone https://github.com/klebutt/synth-analogue-experiments.git
cd synth-analogue-experiments
pip install -r requirements.txt
```

### Quick Start
1. Check out the example notebook in `notebooks/01_getting_started.ipynb`
2. Run the hello-world miner script: `python scripts/hello_world_miner.py`
3. Explore the baseline models in `models/baseline/`

## Development Roadmap

### Phase 1: Foundation (Current)
- [x] Project structure setup
- [ ] Baseline model implementations
- [ ] Basic testing framework
- [ ] Documentation structure

### Phase 2: Analog Models
- [ ] Research analog-inspired approaches
- [ ] Implement first analog forecasting module
- [ ] Compare performance against baselines
- [ ] Optimize for Synth subnet requirements

### Phase 3: Integration
- [ ] Connect to Synth subnet
- [ ] Performance validation
- [ ] TAO earning optimization

## Key Concepts

**CRPS (Continuous Ranked Probability Score)**: The metric Synth uses to evaluate predictions. Lower scores = better predictions. Think of it as measuring how well your probability forecasts match reality.

**Analog-Inspired**: Instead of discrete predictions, we explore continuous, fluid-like mathematical relationships that might capture complex market dynamics better than traditional approaches.

**Synth Subnet**: A Bittensor subnet where you can earn TAO (cryptocurrency) by providing accurate price predictions and synthetic data.

## Contributing

This is a personal research project, but feedback and ideas are welcome! The code is structured to be easily understandable and extensible.

## Resources

- [Synth Subnet Documentation](https://docs.bittensor.com/)
- [CRPS Explanation](https://en.wikipedia.org/wiki/Continuous_ranked_probability_score)
- [Bittensor Network](https://bittensor.com/)

## License

[Add your preferred license here]

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

## Repo Structure
```
synth-analogue-experiments/
├── notebooks/          # Jupyter notebooks for experiments and analysis
├── models/            # Model implementations (baseline + analog-inspired)
├── tests/             # Unit tests and validation
├── docs/              # Documentation and research notes
├── scripts/           # Utility scripts and automation
└── requirements.txt   # Python dependencies
```
