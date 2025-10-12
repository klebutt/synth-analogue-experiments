module.exports = {
  apps: [
    {
      name: "synth-miner",
      interpreter: "python3",
      script: "./neurons/miner.py",
      args: "--netuid 50 --logging.debug --wallet.name wallet1 --wallet.hotkey default --axon.port 8091 --blacklist.force_validator_permit true --blacklist.validator_min_stake 1000",
      env: {
        PYTHONPATH: ".",
      },
      cwd: "/root/synth-subnet",
    },
  ],
};
