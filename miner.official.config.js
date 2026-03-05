module.exports = {
  apps: [
    {
      name: "synth-miner",
      interpreter: "python3.11",
      script: "./neurons/miner.py",
      args: "--netuid 50 --logging.debug --wallet.name wallet1 --wallet.hotkey default --axon.port 8091 --blacklist.force_validator_permit true --blacklist.validator_min_stake 1000",
      env: {
        PYTHONPATH: ".",
      },
      cwd: "/root/synth-subnet",
    },
    {
      name: "synth-dashboard",
      interpreter: "python3.11",
      script: "/root/synth-analogue-experiments/dashboard/app.py",
      env: {
        PYTHONPATH: "/root/synth-analogue-experiments",
        PREDICTION_LOG_PATH: "/root/prediction_log.jsonl",
        FLASK_ENV: "production",
      },
      cwd: "/root/synth-analogue-experiments/dashboard",
      watch: false,
    },
  ],
};
