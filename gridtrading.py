import time
from GridTrader import FtxTrader
trader = FtxTrader("ETH-PERP", 3500, 2700, 15, 0.006)
while True:
    trader.start()
    time.sleep(30)
