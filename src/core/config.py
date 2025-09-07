from pydantic import BaseModel
import yaml, os
from dotenv import load_dotenv

load_dotenv()

class IBKRConfig(BaseModel):
    host: str
    port: int
    clientId: int
    account: str
    primaryExchange: str = "SMART"
    currency: str = "USD"

class DefaultConfig(BaseModel):
    base_ccy: str
    report_dir: str
    calendar: str
    risk: dict

class StratConfig(BaseModel):
    universe: dict
    signal: dict
    execution: dict

class Settings(BaseModel):
    default: DefaultConfig
    ibkr: IBKRConfig
    strat: StratConfig


def load_yaml(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_settings() -> Settings:
    default = load_yaml("config/default.yaml")
    ibkr = load_yaml("config/venues/ibkr.yaml")
    strat = load_yaml("config/strategy/vobreakout.yaml")
    # env override
    for k in ("host", "port", "clientId", "account"):
        env = os.getenv(f"IB_{k.upper()}")
        if env is not None:
            if k in ("port", "clientId"):
                ibkr[k] = int(env)
            else:
                ibkr[k] = env
    return Settings(default=DefaultConfig(**default), ibkr=IBKRConfig(**ibkr), strat=StratConfig(**strat))
