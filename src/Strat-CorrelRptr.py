#######################################
# Author: James Ma
# Email stuff here: jamesmawm@gmail.com
#######################################

""" Strategy: Correlation Reporter

Prints the correlations using Pandas.
"""

import pandas as pd
import ibDataTypes as DataType
import ibHFT


class TradingStrategy:

    def __init__(self):
        self.ibhft = None
        self.pd_last_prices = pd.DataFrame()
        self.stocks_to_stream = ["JPM", "USB", "C", "WFC", "BAC", "MS"]
        self.duration = DataType.DURATION_1_DAY
        self.interval = DataType.BAR_SIZE_1_MIN
        return

    def process_historical_data(self, msg):
        print msg

        vwap = msg.WAP
        stock_index = msg.reqId
        if vwap != -1:
            stock_code = self.stocks_to_stream[stock_index]
            date_time = msg.date
            #open = msg.open
            #high = msg.high
            close = msg.close
            #volume = msg.volume

            self.pd_last_prices = self.pd_last_prices.set_value(date_time, stock_code, close)

        elif vwap == -1:
            if len(self.pd_last_prices.columns) == len(self.stocks_to_stream):
                self.on_completion()

    def on_completion(self):
        self.ibhft.set_is_shutdown()
        print self.pd_last_prices.corr()

    def run(self):
        self.ibhft = ibHFT.IbHFT()
        self.ibhft.set_connection_with_api_gateway(False)
        self.ibhft.start_historical_data_stream(self.stocks_to_stream
                                                , self.duration
                                                , self.interval
                                                , self.process_historical_data)

if __name__ == '__main__':
    TradingStrategy().run()