# everlong-bot
A bot repo for fuzzing and interacting with the everlong contract.

This repo contains 2 scripts:
- `scripts/run_everlong_keeper.py` connects to a remote chain and runs the following keeper functions periodically.
  - `update_debt`
  - `tend`
  - `strategyReport`
  - `processReport`

- `scripts/fuzz_everlong.py` spins up a local fork of mainnet, and runs:
  - Random trades on the underlying hyperdrive pool.
  - Random deposit and redeems from the vault.
  - The keeper functions.

## Local Installation
Check out this repo, and install it as a package. We recommend installing within a virtual environment (e.g., [uv](https://github.com/astral-sh/uv))

```
cd <path-to-repo>
uv venv -p 3.10 .venv
source .venv/bin/activate
uv pip install .[all]
```

## Everlong keeper bot
The everlong keeper bot script aims to periodically call the maintenance functions for everlong. To run, copy `.env.sample` to `.env` and fill out the appropriate fields for the everlong bot env, i.e.:

- `MAINNET_RPC_URI`
- `KEEPER_PRIVATE_KEY`
- `KEEPER_CONTRACT_ADDRESS`

The script can then be ran via

```
python scripts/run_everlong_keeper.py
```

## Everlong fuzzing
The everlong fuzzing framework script aims to launch a local mainnet fork and run random trades on the underlying hyperdrive pool, the everlong vault, and the everlong keeper bot in this environment. To run, copy `.env.sample` to `.env` and fill out ht eappropriate fields for the fuzzing framework, i.e.:

- `MAINNET_RPC_URI`
- `KEEPER_PRIVATE_KEY`
- `HYPERDRIVE_ADDRESS`
- `EVERLONG_PATH`
- `DEPLOYER_PRIVATE_KEY`
- `GOVERNANCE_PRIVATE_KEY`
- `MANAGEMENT_PRIVATE_KEY`
- `EMERGENCY_ADMIN_PRIVATE_KEY`

The script can then be ran via

```
python scripts/fuzz_everlong.py
```

## Type generation
Under `everlong_bot/everlong_types` lies the [pypechain](https://github.com/delvtech/pypechain) generated types for the abis from everlong. To regenerate the types when e.g., the contract interfaces change, set the `EVERLONG_PATH` environment variable to the local path of the [everlong repo](https://github.com/delvtech/everlong), and run `make`. This will (1) compile the everlong contracts, and (2) run pypechain on the output abis.



