import time
from GridTrader import FtxTrader
#(market, top of the grid, bottom of the grid, grid number, qty)
trader = FtxTrader("ETH-PERP", 3500, 2700, 15, 0.006)
while True:
    trader.start()
    #Loop interval
    time.sleep(10)
