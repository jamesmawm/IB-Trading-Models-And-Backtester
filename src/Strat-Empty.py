#######################################
# Author: James Ma
# Email stuff here: jamesmawm@gmail.com
#######################################

""" Template Strategy

An empty template to create strategies.
"""

import Backtester.Backtester as bt
import ibHFT

# Changeable params
STOCKS_TO_STREAM = ["PEP", "KO"]


class TradingStrategy:

    def __init__(self):
        self.ibhft = None
        return

    def on_position_changed(self):
        print "on position changed."

    def on_tick(self, ticks, stock_code, field_type):
        print "tick"

    def on_started(self):
        return

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
    # TradingStrategy().run()
    TradingStrategy().run_backtest()