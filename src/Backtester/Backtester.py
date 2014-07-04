#######################################
# Author: James Ma
# Email stuff here: jamesmawm@gmail.com
#######################################

from ibHFT import IbHFT
from StubTickEvent import StubTickEvent as TickEvent
from StubOrderEvent import StubOrderEvent as OrderEvent
import csv
import pandas as pd
import ibDataTypes


class Backtester(IbHFT):

    def __init__(self):
        IbHFT.__init__(self)
        self.COST_PER_SHARE = 0.005
        self.on_tick_func = None
        self.on_position_changed_func = None
        self.csv_file = None

    def set_csv_file(self, filename):
        self.csv_file = filename

    def start_data_stream(self, on_started_func, on_tick, stock_codes, on_pos_changed=None):
        dataframe = pd.read_csv(self.csv_file)
        csv_stock_codes = [stock_code for stock_code in dataframe][1:]

        self.init_context(csv_stock_codes)
        self.assign_functions(on_pos_changed, on_tick)

        for row in range(dataframe.shape[0]):
            self.on_data_row(dataframe, row, stock_codes)

        self.report_backtest_results()

    def report_backtest_results(self):
        print "Back results:"

        position = {k: 0 for k in self.stock_codes}
        pnl = 0
        for order in self.orders_filled:

            qty = order.qty
            stock_code = order.stock_code
            comm = self.get_commission(qty)
            is_buy = order.is_buy
            price = order.price
            mkt_value = qty * price
            position[stock_code] += qty * (1 if is_buy else -1)
            pnl += mkt_value * (1 if not is_buy else -1) - comm

            print order.filled_time, stock_code, price, "B" if order.is_buy else "S", qty, position[stock_code], pnl

    def get_commission(self, qty):
        return max(1, self.COST_PER_SHARE*qty)

    def on_data_row(self, dataframe, row, stock_codes):
        current_time = None
        for i, header in enumerate(dataframe):
            if i == 0:
                current_time = dataframe[header][row]
            else:
                ticker_id = i-1
                stock_code = header

                ''' TODO: retrive previous last price and dont' send tick event if same
                '''

                tick_event = TickEvent()
                tick_event.tickerId = ticker_id
                tick_event.price = dataframe[stock_code][row]
                tick_event.typeName = ibDataTypes.MSG_TYPE_TICK_PRICE
                tick_event.field = ibDataTypes.FIELD_LAST_PRICE
                self.send_event_tick(tick_event, current_time)

                bid_event = TickEvent()
                bid_event.tickerId = ticker_id
                bid_event.price = dataframe[stock_code][row] - 0.01
                bid_event.typeName = ibDataTypes.MSG_TYPE_TICK_PRICE
                bid_event.field = ibDataTypes.FIELD_BID_PRICE
                self.send_event_tick(bid_event, current_time)

                ask_event = TickEvent()
                ask_event.tickerId = ticker_id
                ask_event.price = dataframe[stock_code][row] + 0.01
                ask_event.typeName = ibDataTypes.MSG_TYPE_TICK_PRICE
                ask_event.field = ibDataTypes.FIELD_ASK_PRICE
                self.send_event_tick(ask_event, current_time)

    def send_event_tick(self, msg, current_time):
        self.tick_event(msg)
        self.match_orders(current_time)

    def match_orders(self, timestamp):

        for pending_order in self.orders_pending:
            stock_code = pending_order.stock_code
            current_bid_px = self.get_current_bid_price(stock_code)
            current_ask_px = self.get_current_ask_price(stock_code)
            order_px = pending_order.price
            is_buy = pending_order.is_buy
            order_id = pending_order.order_id

            if (is_buy and order_px >= current_ask_px) \
                or (not is_buy and order_px <= current_bid_px):

                pending_order.filled_time = timestamp
                self.execute_order(order_id)

    def execute_order(self, order_id):
        order_event = OrderEvent()
        order_event.orderId = order_id
        order_event.typeName = ibDataTypes.MSG_TYPE_ORDER_STATUS
        order_event.status = ibDataTypes.ORDER_STATUS_FILLED
        order_event.remaining = 0
        self.logger(order_event)

    @staticmethod
    def read_csv_file(filepath):
        with open(filepath, "rb") as fileobject:
            return csv.reader(fileobject)
        return None

    #Override
    def replace_order(self, order):
        return

    #Override
    def cancel_order(self, order):
        return

    #Override
    def place_order(self, this_order_id, tradable, stock_order):
        return