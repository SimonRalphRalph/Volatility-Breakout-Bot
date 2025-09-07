from ib_insync import IB, Stock, LimitOrder, StopOrder
from src.core.types import Target
from src.core.config import load_settings
from src.core.log import logger

class Executor:
    def __init__(self, ib: IB):
        self.ib = ib
        self.venue = load_settings().ibkr

    def stock(self, symbol: str) -> Stock:
        return Stock(symbol, "SMART", self.venue.currency, primaryExchange=self.venue.primaryExchange)

    def place_bracket(self, t: Target):
        c = self.stock(t.symbol)
        entry = LimitOrder("BUY" if t.qty>0 else "SELL", abs(t.qty), t.entry_limit)
        entry.tif = "DAY"
        entry.account = self.venue.account

        stop = StopOrder("SELL", abs(t.qty), t.stop_loss) if t.qty>0 else StopOrder("BUY", abs(t.qty), t.stop_loss)
        stop.tif = "DAY"
        stop.account = self.venue.account

        trade = self.ib.placeOrder(c, entry)
        self.ib.sleep(0.1)
        self.ib.waitOnUpdate(timeout=5)
        oid = trade.order.orderId
        logger.info(f"Entry submitted {t.symbol} oid={oid} qty={t.qty} limit={t.entry_limit:.2f}")

        stop.parentId = oid
        trade_sl = self.ib.placeOrder(c, stop)
        logger.info(f"Stop submitted {t.symbol} parent={oid} stop={t.stop_loss:.2f}")
        return oid
