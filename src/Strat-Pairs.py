#######################################
# Author: James Ma
# Email stuff here: jamesmawm@gmail.com
#######################################

""" Strategy: Pairs trading through cointegration

Uses OLS to determine order of co-integration every self.window_length.
Pair-trading by mean-reversion.
"""

import Backtester.Backtester as bt
import pandas as pd
from pandas.stats.api import ols
from Tkinter import *
import ibHFT
import threading
import ibDataTypes
import time
import numpy as np

# Fixed params
TICK_SIZE = 0.01

# Changeable params
STOCKS_TO_STREAM = ["C", "MS", "BAC"]
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
        self.pd_last_prices = pd.DataFrame()
        self.tk = Tk()
        self.label_stock = StringVar()
        self.label_bidask = StringVar()
        self.label_last = StringVar()
        self.label_ticks = StringVar()
        self.label_position = StringVar()
        self.label_orders = StringVar()
        self.label_pnl = StringVar()
        self.label_zscore = StringVar()
        self.label_traded = StringVar()
        self.spreads = []
        self.window_length = 30
        self.is_bootstrapped = False
        return

    def sample_ticks_at_interval(self):

        if self.current_state is not self.STATE_TERMINATED:
            self.current_sampling_thread = threading.Timer(1.0, self.sample_ticks_at_interval).start()

        if self.current_ticks is None:
            return

        store_time = time.strftime(ibDataTypes.DATE_TIME_FORMAT)

        for stock_code, stock_tick in self.current_ticks.iteritems():
            self.pd_last_prices = self.pd_last_prices.set_value(store_time
                                                                , stock_code
                                                                , stock_tick.last_price)

        rows = self.pd_last_prices.shape[0]
        if rows > self.window_length:
            self.is_bootstrapped = True
            self.pd_last_prices = self.pd_last_prices[-self.window_length:]

    def on_tick(self, ticks, stock_code, field_type):
        self.current_ticks = ticks

        if not self.is_bootstrapped:
            print "Bootstrapping...."
            return

        [stock_code_a, stock_code_b, stock_code_c] = STOCKS_TO_STREAM

        # Assign prices of interest
        get_last_prices = lambda code: self.pd_last_prices[code]
        prices_a = get_last_prices(stock_code_a)
        prices_b = get_last_prices(stock_code_b)

        a_last_px, a_bid_px, a_ask_px = self.get_current_prices(stock_code_a)
        b_last_px, b_bid_px, b_ask_px = self.get_current_prices(stock_code_b)

        if a_bid_px == 0 or a_ask_px == 0 or b_bid_px == 0 or b_ask_px == 0:
            return

        # Do OLS for coeffs
        slope1, intercept1, mean1, stdev1 = self.get_coeffs_from_ols(prices_a, prices_b)
        spread_lasta_lastb = self.calculate_spread(a_last_px, b_last_px, slope1, intercept1)
        zscore = self.get_zscore(spread_lasta_lastb, mean1, stdev1)

        is_have_pending_orders = (self.ibhft.get_number_of_pending_orders() > 0)
        a_pos = self.ibhft.get_position(stock_code_a)
        b_pos = self.ibhft.get_position(stock_code_b)
        is_position_flat = a_pos == 0 and b_pos == 0

        if zscore >= 2.0 and not is_have_pending_orders and is_position_flat:
            self.ibhft.place_limit_order(stock_code_a, False, TRADE_QTY, a_bid_px)
            self.ibhft.place_limit_order(stock_code_b, True,  TRADE_QTY, b_ask_px)

        elif zscore <= -2.0 and not is_have_pending_orders and is_position_flat:
            self.ibhft.place_limit_order(stock_code_a, True, TRADE_QTY, a_ask_px)
            self.ibhft.place_limit_order(stock_code_b, False,  TRADE_QTY, b_bid_px)

        elif abs(zscore) < .5 and not is_have_pending_orders and not is_position_flat:
            (is_buy_a, a_px) = (True, a_ask_px) if a_pos < 0 else (False, a_bid_px)
            (is_buy_b, b_px) = (True, b_ask_px) if b_pos < 0 else (False, b_bid_px)
            self.ibhft.place_limit_order(stock_code_a, is_buy_a, TRADE_QTY, a_px)
            self.ibhft.place_limit_order(stock_code_b, is_buy_b,  TRADE_QTY, b_px)

        elif is_have_pending_orders:

            is_mkt_went_away_on_both_sides = True
            for order in self.ibhft.get_pending_orders():
                code = order.stock_code
                last_px, bid_px, ask_px = self.get_current_prices(code)
                mkt_px = ask_px if order.is_buy else bid_px
                ticks_diff = abs(mkt_px - order.price)

                if ticks_diff <= 0.02:
                    is_mkt_went_away_on_both_sides = False

            if is_mkt_went_away_on_both_sides:
                self.ibhft.remove_all_pending_orders()

        self.update_ui(zscore)

    def get_coeffs_from_ols(self, a, b):
        slope, intercept = ols(y=a, x=b).beta[['x', 'intercept']]
        spreads_pair_ab = self.calculate_spread(a, b, slope, intercept)
        mean, stdev = self.get_mean_and_std(spreads_pair_ab)
        return slope, intercept, mean, stdev

    @staticmethod
    def get_mean_and_std(values):
        return np.mean(values), np.std(values)

    @staticmethod
    def calculate_spread(a, b, slope, intercept):
        return a - (b * slope + intercept)

    @staticmethod
    def get_zscore(a, mean, stdev):
        return 0 if stdev==0 else (a-mean)/stdev

    def get_current_prices(self, code):
        last_px = self.ibhft.get_current_last_price(code)
        bid_px = self.ibhft.get_current_bid_price(code)
        ask_px = self.ibhft.get_current_ask_price(code)
        return last_px, bid_px, ask_px

    def flush_sampled_data_to_csv(self, filename):
        self.pd_last_prices.to_csv(filename, sep=',', encoding='utf-8')

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

    def update_ui(self, zscore):
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
        self.label_zscore.set("{0:.3f}".format(zscore))

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
        row_index = create_row("Z-score:", self.label_zscore, row_index)

    def on_started(self):
        self.sample_ticks_at_interval()
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
        def setup_bootstrap_conditions():
            self.pd_last_prices = pd.read_csv("ticks 10 mins - Jun 25 2014.csv")
            self.pd_last_prices = self.pd_last_prices[-self.window_length:]
            self.is_bootstrapped = True

        setup_bootstrap_conditions()
        self.ibhft = bt.Backtester()
        self.ibhft.set_csv_file("ticks 10 mins - Jun 25 2014.csv")
        self.ibhft.start_data_stream(self.on_started
                                     , self.on_tick
                                     , STOCKS_TO_STREAM
                                     , self.on_position_changed)

if __name__ == '__main__':
    # TradingStrategy().run()
    TradingStrategy().run_backtest()