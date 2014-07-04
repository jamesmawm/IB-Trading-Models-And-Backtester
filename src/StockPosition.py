#######################################
# Author: James Ma
# Email stuff here: jamesmawm@gmail.com
#######################################

from ibUtil import *


class StockPosition:

    def __init__(self, stock_code):
        self.stock_code = stock_code
        self.position = 0
        self.market_value = 0
        self.average_price = 0
        self.realized_pnl = 0
        self.unrealized_pnl = 0
        self.tradable = create_stock_contract(self.stock_code)