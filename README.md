# Volatility Breakout Bot
Aggressive but risk-managed US small/mid-cap breakout strategy with strict stops, executed via IBKR.

## Quickstart
```bash
# 1) Install Poetry, then
poetry install

# 2) Configure
cp .env.example .env  # fill IB_* and POLYGON_API_KEY

# 3) Smoke test
poetry run pytest -q

# 4) Run the EOD job (paper)
poetry run python -m src.apps.eod_rebalance --mode paper --run-id $(date +%Y%m%d)
