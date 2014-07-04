#######################################
# Author: James Ma
# Email stuff here: jamesmawm@gmail.com
#######################################

""" Strategy: Limit Orders

Place limit orders just above the bid ask prices.
Close position when exceed certain thresholds.
"""

import Backtester.Backtester as bt
from Tkinter import *
import ibHFT

# Fixed params
TICK_SIZE = 0.01

# Changeable params
STOCKS_TO_STREAM = ["C", "JPM"]
CLCYLE_LIMIT = 3
TRADE_QTY = 100
LMT_ORDER_SIZE = 0.01
SPREAD_TICKS_TO_TRADE = 0.01
TAKE_PROFIT_TICKS = TICK_SIZE * 1
MAX_TICKS_LOSS = 0.03


class TradingStrategy:

    # Strategy states
    STATE_PLACE_ORDERS = 0
    STATE_POSITION_OPENED = 1
    STATE_TERMINATED = 2

    def __init__(self):
        self.ibhft = None
        self.current_state = self.STATE_PLACE_ORDERS
        self.current_ticks = None
        self.sell_px = self.buy_px = self.working_ask_px = self.working_bid_px = 0
        self.tx_px = self.limit_px = self.loss_px = 0
        self.current_cycle = 0
        self.current_sampling_thread = None
        self.tk = Tk()
        self.label_stock = StringVar()
        self.label_bidask = StringVar()
        self.label_last = StringVar()
        self.label_ticks = StringVar()
        self.label_position = StringVar()
        self.label_orders = StringVar()
        self.label_pnl = StringVar()
        self.label_cycle = StringVar()
        self.label_traded = StringVar()
        return

    def on_tick(self, ticks, stock_code, field_type):
        self.current_ticks = ticks

        stock_a = STOCKS_TO_STREAM[0]
        is_position_flat = self.ibhft.is_position_flat(stock_a)
        if self.is_no_open_orders() \
                and is_position_flat \
                and self.current_state == self.STATE_PLACE_ORDERS:

            self.place_limit_orders(ticks, stock_a)

        elif not is_position_flat:
            self.monitor_to_cover_position(stock_a)

        # Else, wait for trade execution.

        self.update_ui()

    def monitor_to_cover_position(self, stock_code):
        pos = self.ibhft.get_position(stock_code)
        if pos != 0:
            if self.current_state == self.STATE_PLACE_ORDERS:
                self.current_state = self.STATE_POSITION_OPENED
                self.send_take_profit_limit_order(stock_code, pos)

            elif self.current_state == self.STATE_POSITION_OPENED:
                self.update_covering_position(stock_code, pos)

    def update_covering_position(self, stock_code, pos):
        if pos == 0:
            return

        current_bid_px = self.ibhft.get_current_bid_price(stock_code)
        current_ask_px = self.ibhft.get_current_ask_price(stock_code)

        is_long = pos > 0
        self.tx_px = self.buy_px if is_long else self.sell_px
        market_px = current_bid_px if is_long else current_ask_px
        ticks_lost = max(0, self.tx_px - market_px) if is_long else max(0, market_px - self.tx_px)

        self.loss_px = self.tx_px - MAX_TICKS_LOSS if is_long else self.tx_px + MAX_TICKS_LOSS

        pendings = self.ibhft.get_number_of_pending_orders()
        if ticks_lost >= MAX_TICKS_LOSS:

            if pendings == 1:
                self.ibhft.place_limit_order(stock_code, not is_long, TRADE_QTY, market_px)

                stock_order = self.ibhft.get_pending_orders()[0]
                self.limit_px = stock_order.price

            elif pendings > 1:
                self.update_market_order(market_px, not is_long)

        else:

            if pendings == 1:
                stock_order = self.ibhft.get_pending_orders()[0]
                self.limit_px = stock_order.price

            if pendings > 1:
                self.remove_market_order()

    def remove_market_order(self):
        max_order_id = max([stock_order.order_id for stock_order in self.ibhft.get_pending_orders()])
        self.ibhft.remove_pending_order(max_order_id)

    def update_market_order(self, new_px, is_buy):
        max_order_id = max([stock_order.order_id for stock_order in self.ibhft.get_pending_orders()])
        for stock_order in self.ibhft.get_pending_orders():
            if stock_order.order_id == max_order_id:
                if stock_order.price != new_px \
                        or stock_order.is_buy != is_buy:
                    stock_order.price = new_px
                    stock_order.is_buy = is_buy
                    self.ibhft.replace_order(stock_order)
                    return

    def send_take_profit_limit_order(self, stock_code, pos):

        if pos < 0:
            # Cover position - Go LONG at bid px.
            self.current_state = self.STATE_POSITION_OPENED
            take_profit_px = self.sell_px - TAKE_PROFIT_TICKS
            self.update_pending_order(stock_code, take_profit_px)

        elif pos > 0:
            # Cover position - Go SHORT at ask px.
            self.current_state = self.STATE_POSITION_OPENED
            take_profit_px = self.buy_px + TAKE_PROFIT_TICKS
            self.update_pending_order(stock_code, take_profit_px)

    def update_pending_order(self, stock_code, new_price):
        for order in self.ibhft.get_pending_orders():
            if order.stock_code == stock_code:
                self.ibhft.update_order_with_price_and_type(order, new_price, None)
                return

    def on_position_changed(self):
        stock_a = STOCKS_TO_STREAM[0]

        if self.ibhft.is_position_flat(stock_a):
            self.ibhft.remove_all_pending_orders()

        if self.current_state == self.STATE_POSITION_OPENED:
            self.current_cycle += 1
            if self.current_cycle < CLCYLE_LIMIT:
                self.current_state = self.STATE_PLACE_ORDERS
            else:
                self.current_state = self.STATE_TERMINATED
                self.tk.quit()
                print "Cycle completed."

    def is_no_open_orders(self):
        num_open_orders = self.ibhft.get_number_of_pending_orders()
        return num_open_orders == 0

    def place_limit_orders(self, ticks, stock_code):
        a_bid_px = ticks[stock_code].bid_price
        a_ask_px = ticks[stock_code].ask_price

        if a_bid_px == 0 or a_ask_px == 0:
            return

        self.working_bid_px = a_bid_px
        self.working_ask_px = a_ask_px
        self.buy_px = self.working_bid_px - LMT_ORDER_SIZE
        self.sell_px = self.working_ask_px + LMT_ORDER_SIZE

        self.ibhft.place_limit_order(stock_code, True, TRADE_QTY, self.buy_px)
        self.ibhft.place_limit_order(stock_code, False, TRADE_QTY, self.sell_px)

    def update_ui(self):
        stock_a = STOCKS_TO_STREAM[0]
        self.label_stock.set(stock_a)

        bidaskstr = "({bidvol}) {bid}/{ask} ({askvol})".format(
            bidvol=self.current_ticks[stock_a].bid_volume
            , bid=self.current_ticks[stock_a].bid_price
            , ask=self.current_ticks[stock_a].ask_price
            , askvol=self.current_ticks[stock_a].ask_volume)
        self.label_bidask.set(bidaskstr)

        laststr = "{last} ({lastvol})".format(
            last=self.current_ticks[stock_a].last_price
            , lastvol=self.current_ticks[stock_a].last_volume)
        self.label_last.set(laststr)

        ordersstr = "{pending} / {working}".format(
            pending=self.ibhft.get_number_of_pending_orders()
            , working=self.ibhft.get_number_of_filled_orders())
        self.label_orders.set(ordersstr)

        a_position = self.ibhft.get_stock_position(stock_a)
        pnlstr = "{unreal} / {real}".format(
            unreal=a_position.unrealized_pnl
            , real=a_position.realized_pnl)
        self.label_pnl.set(pnlstr)

        self.label_position.set(self.ibhft.get_position(stock_a))

        self.label_ticks.set(self.ibhft.get_number_of_ticks())

        cyclestr = "{cyc} / {cycmax}".format(
            cyc=self.current_cycle
            , cycmax=CLCYLE_LIMIT)
        self.label_cycle.set(cyclestr)

        tradedstr = "{traded} ({limit}/{loss})".format(
            traded=self.tx_px
            , limit=self.limit_px
            , loss=self.loss_px)
        self.label_traded.set(tradedstr)

    def create_ui(self):

        def create_row(header, label, row):
            Label(self.tk, text=header).grid(row=row,column=0)
            Label(self.tk, textvariable=label).grid(row=row,column=1)
            row += 1
            return row

        row_index = 0
        row_index = create_row("Stock:", self.label_stock, row_index)
        row_index = create_row("Bid/Ask:", self.label_bidask, row_index)
        row_index = create_row("Last:", self.label_last, row_index)
        row_index = create_row("Traded:", self.label_traded, row_index)
        row_index = create_row("Unreal/Real:", self.label_pnl, row_index)
        row_index = create_row("Pending/Filled", self.label_orders, row_index)
        row_index = create_row("Position:", self.label_position, row_index)
        row_index = create_row("Ticks:", self.label_ticks, row_index)
        row_index = create_row("Cycle:", self.label_cycle, row_index)

    def on_started(self):
        self.create_ui()
        self.tk.mainloop()

        if self.current_sampling_thread is not None:
            self.current_sampling_thread.cancel()

    def run(self):
        self.ibhft = ibHFT.IbHFT()
        self.ibhft.set_connection_with_api_gateway(False)
        self.ibhft.start_data_stream(self.on_started
                                     , self.on_tick
                                     , STOCKS_TO_STREAM
                                     , self.on_position_changed)

    def run_backtest(self):
        self.ibhft = bt.Backtester()
        self.ibhft.set_csv_file("ticks 10 mins - Jun 25 2014.csv")
        self.ibhft.start_data_stream(self.on_started
                                     , self.on_tick
                                     , STOCKS_TO_STREAM
                                     , self.on_position_changed)

if __name__ == '__main__':
    TradingStrategy().run()
    # TradingStrategy().run_backtest()