#######################################
# Author: James Ma
# Email stuff here: jamesmawm@gmail.com
#######################################

from ibUtil import *


class StockOrder:
    def __init__(self, order_id, stock_code, is_buy, qty, price=None, stop_price = None):
        self.order_id = order_id
        self.stock_code = stock_code
        self.is_buy = is_buy
        self.qty = qty
        self.price = price
        self.stop_price = stop_price
        self.filled_timed = None

    def get_stock_order(self):
        return create_stock_order(self.order_id, self.qty, self.is_buy, self.price, self.stop_price)

    def get_order_position(self):
        return self.qty * (1 if self.is_buy else -1)
