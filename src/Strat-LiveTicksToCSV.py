#######################################
# Author: James Ma
# Email stuff here: jamesmawm@gmail.com
#######################################

""" Strategy: Live Ticks Collector

Collects X amount of ticks and write to CSV file.
"""

from ibHFT import *
import pandas as pd
import ibDataTypes
import threading

# Changeable variables
stocks_to_stream = ["JPM", "USB", "C", "WFC", "BAC", "MS"]
filename = "ticks 10 mins.csv"
minutes_to_collect = 10
ticks_to_collect = 60 * minutes_to_collect  # Or number of seconds to collect
tick_interval_in_seconds = 1.0

# Global variables
is_finish_collecting_ticks = False
current_ticks = None
pd_last_prices = pd.DataFrame()


def sample_ticks_at_interval():
    global is_finish_collecting_ticks
    if is_finish_collecting_ticks:
        return

    threading.Timer(tick_interval_in_seconds, sample_ticks_at_interval).start()

    store_current_tick()
    print len(pd_last_prices.index), "of", ticks_to_collect, "collected..."

    if len(pd_last_prices.index) >= ticks_to_collect:
        is_finish_collecting_ticks = True
        flush_ticks_to_file(pd_last_prices)
        print "Ticks written to", filename, "completed."


def store_current_tick():
    global current_ticks, pd_last_prices

    if current_ticks is None:
        return

    store_time = time.strftime(ibDataTypes.DATE_TIME_FORMAT)
    for stock_code, stock_tick in current_ticks.iteritems():
        pd_last_prices = pd_last_prices.set_value(store_time, stock_code, stock_tick.last_price)


def flush_ticks_to_file(last_prices_pd):
    last_prices_pd.to_csv(filename, sep=',', encoding='utf-8')


def on_tick(ticks, stock_code, field_type):
    global current_ticks
    current_ticks = ticks
    print ticks


def on_start():
    sample_ticks_at_interval()


def main():
    set_connection_with_api_gateway(False)
    start_data_stream(on_start, on_tick, stocks_to_stream)

if __name__ == '__main__':
    main()