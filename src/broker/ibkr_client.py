from ib_insync import IB
from src.core.config import load_settings
from src.core.log import logger

class IbClient:
    def __init__(self):
        self.cfg = load_settings().ibkr
        self.ib = IB()

    async def connect(self):
        logger.info(f"Connecting IBKR {self.cfg.host}:{self.cfg.port} cid={self.cfg.clientId}")
        await self.ib.connectAsync(self.cfg.host, self.cfg.port, clientId=self.cfg.clientId)
        logger.info("Connected to IBKR")

    def account(self) -> str:
        return self.cfg.account
