#######################################
# Author: James Ma
# Email stuff here: jamesmawm@gmail.com
#######################################

import numpy as np
from ib.opt import ibConnection, message
from ib.opt import Connection
import time
from time import strftime
from StockTradable import *
from StockPosition import *
from StockOrder import *


class IbHFT:

    def __init__(self):
        self.is_use_gateway = True
        self.is_shutdown = False
        self.account_code = ""
        self.conn = None
        self.number_of_ticks = 0
        self.order_id = 0
        self.orders_pending = np.array([])
        self.stock_ticks_dict = {}
        self.orders_filled = np.array([])
        self.on_tick_func = None
        self.positions_dict = {}
        self.stock_codes = np.array([])
        self.on_position_changed_func = None
        self.on_historical_data_func = None
        return

    '''
    Callable methods from inherited parent.
    '''
    def get_current_bid_price(self, stock_code):
        return self.stock_ticks_dict[stock_code].bid_price

    def get_current_ask_price(self, stock_code):
        return self.stock_ticks_dict[stock_code].ask_price

    def get_current_last_price(self, stock_code):
        return self.stock_ticks_dict[stock_code].last_price

    def place_limit_order(self, stock_code, is_buy, qty, price):
        this_order_id = self.get_order_id_and_increment()
        tradable = self.get_tradable(stock_code)
        stock_order = StockOrder(this_order_id, stock_code, is_buy, qty, price)
        self.place_order_and_add_to_list(this_order_id, tradable, stock_order)

    def place_order_and_add_to_list(self, this_order_id, tradable, stock_order):
        self.place_order(this_order_id, tradable, stock_order)
        self.add_pending_order(stock_order)

    def set_is_shutdown(self):
        self.is_shutdown = True

    def get_number_of_ticks(self):
        return self.number_of_ticks

    def update_order_with_price_and_type(self, order, new_price, stop_price):
        order.price = new_price
        order.stop_price = stop_price
        self.replace_order(order)

    def replace_order(self, order):
        tradable = self.get_tradable(order.stock_code)
        self.conn.placeOrder(order.order_id
                             , tradable
                             , order.get_stock_order())

    def remove_all_pending_orders(self):
        for order in self.orders_pending:
            self.cancel_order(order.order_id)

        self.orders_pending = np.array([])

    def remove_pending_order(self, order_id_to_delete):
        for i, order in enumerate(self.orders_pending):
            if order.order_id == order_id_to_delete:
                self.cancel_order(order.order_id)
                self.orders_pending = np.delete(self.orders_pending, i)
                return

    def add_pending_order(self, stock_order):
        self.orders_pending = np.hstack((self.orders_pending, stock_order))

    def get_pending_orders(self):
        return self.orders_pending

    def get_order_id_and_increment(self):
        working_order_id = self.order_id
        self.order_id += 1
        return working_order_id

    def get_tradable(self, stock_code):
        return self.positions_dict[stock_code].tradable

    def get_number_of_pending_orders(self):
        return len(self.orders_pending)

    def get_number_of_filled_orders(self):
        return len(self.orders_filled)

    # def place_market_order(self, stock_code, is_buy, qty):
    #     stock_contract = self.get_tradable(stock_code)
    #     order = create_stock_order(qty, is_buy, True)
    #     self.conn.placeOrder(self.order_id, stock_contract, order)

    def is_position_flat(self, stock_code):
        return self.get_position(stock_code) == 0

    def get_position(self, stock_code):
        return self.get_stock_position(stock_code).position

    def get_stock_position(self, stock_code):
        return self.positions_dict[stock_code]

    '''
    Local methods
    '''
    def logger(self, msg):

        if msg.typeName == DataType.MSG_TYPE_HISTORICAL_DATA:
            if self.on_historical_data_func is not None:
                self.on_historical_data_func(msg)
            return

        elif msg.typeName == DataType.MSG_TYPE_UPDATE_PORTFOLIO:
            self.process_portfolio_updates(msg)

        elif msg.typeName == DataType.MSG_TYPE_ACCOUNT_UPDATE:
            self.process_account_updates(msg)

        elif msg.typeName == DataType.MSG_TYPE_MANAGED_ACCOUNTS:
            self.set_account_code(msg.accountsList)

        elif msg.typeName == DataType.MSG_TYPE_NEXT_ORDER_ID:
            self.set_order_id(msg.orderId)

        elif msg.typeName == DataType.MSG_TYPE_ORDER_STATUS:
            self.update_order_status(msg)

        elif msg.typeName == DataType.MSG_TYPE_ERROR:
            self.process_error_message(msg)

        else:
            print "logger: " , msg

    def process_error_message(self, msg):

        if msg.errorCode == DataType.ERROR_CODE_MARKET_DATA_FARM_CONNECTED:
            print msg.errorMsg

        elif msg.errorCode == DataType.ERROR_CODE_HISTORICAL_DATA_FARM_CONNECTED:
            print msg.errorMsg

        elif msg.errorCode == DataType.ERROR_CODE_ORDER_CANCELED:
            print msg.errorMsg

        else:
            print "Unhandled errcode: ", msg

    def process_account_updates(self, msg):
        # Do nothing for now
        return

    def process_portfolio_updates(self, msg):
        try:
            for stock_code in self.positions_dict:
                if stock_code == msg.contract.m_symbol:
                    self.positions_dict[stock_code].position = msg.position
                    self.positions_dict[stock_code].market_value = msg.marketValue
                    self.positions_dict[stock_code].average_price = msg.averageCost
                    self.positions_dict[stock_code].realized_pnl = msg.realizedPNL
                    self.positions_dict[stock_code].unrealized_pnl = msg.unrealizedPNL
                    return

        except Exception, e:
            print "process_portfolio_updates err:", e

    def get_positions(self):
        return self.positions_dict

    def set_account_code(self, new_acct_code):
        self.account_code = new_acct_code

    def set_order_id(self, new_order_id):
        self.order_id = new_order_id

    def cancel_order(self, order_id):
        self.conn.cancelOrder(order_id)

    def place_order(self, this_order_id, tradable, stock_order):
        self.conn.placeOrder(this_order_id
                        , tradable
                        , stock_order.get_stock_order())

    def update_order_status(self, msg):
        if msg.status == DataType.ORDER_STATUS_FILLED and msg.remaining == 0:
            self.set_pending_order_as_working(msg.orderId)

            if self.on_position_changed_func is not None:
                self.on_position_changed_func()

    def set_pending_order_as_working(self, this_order_id):
        for i, stock_order in enumerate(self.orders_pending):
            if stock_order.order_id == this_order_id:
                pos = stock_order.get_order_position()
                stock_code = stock_order.stock_code
                self.update_position(stock_code, pos)

                self.orders_filled = np.hstack((self.orders_filled, stock_order))
                self.orders_pending = np.delete(self.orders_pending, i)
                return

    def update_position(self, stock_code, pos):
        self.positions_dict[stock_code].position += pos

    def tick_event(self, msg):
        self.number_of_ticks += 1
        stock_code = self.stock_codes[msg.tickerId]

        if msg.typeName == DataType.MSG_TYPE_TICK_STRING:
            return

        elif msg.typeName == DataType.MSG_TYPE_TICK_PRICE:

            if msg.field == DataType.FIELD_BID_PRICE:
                self.stock_ticks_dict[stock_code].bid_price = msg.price

            elif msg.field == DataType.FIELD_ASK_PRICE:
                self.stock_ticks_dict[stock_code].ask_price = msg.price

            elif msg.field == DataType.FIELD_LAST_PRICE:
                self.stock_ticks_dict[stock_code].last_price = msg.price

        elif msg.typeName == DataType.MSG_TYPE_STICK_SIZE:

            if msg.field == DataType.FIELD_BID_SIZE:
                self.stock_ticks_dict[stock_code].bid_volume = msg.size

            elif msg.field == DataType.FIELD_ASK_SIZE:
                self.stock_ticks_dict[stock_code].ask_volume = msg.size

            elif msg.field == DataType.FIELD_LAST_SIZE:
                self.stock_ticks_dict[stock_code].last_volume = msg.size

            elif msg.field == DataType.FIELD_VOLUME:
                self.stock_ticks_dict[stock_code].volume = msg.size

        else:
            print "Unhandle tick_event: ", msg

        if self.on_tick_func is not None:
            self.on_tick_func(self.stock_ticks_dict, stock_code, msg.field)

    def register_event_handlers(self, ibconn, logger_func=None):
        if logger_func is None:
            logger_func = self.logger

        ibconn.registerAll(logger_func)
        ibconn.unregister(logger_func
                          , message.tickSize
                          , message.tickPrice
                          , message.tickString
                          , message.tickGeneric
                          , message.tickOptionComputation
                          , message.updateAccountTime
                          , message.accountDownloadEnd
                          , message.commissionReport)

        ibconn.register(self.tick_event, message.tickPrice, message.tickSize)

    def request_streaming_data(self, ibconn):
        for i, stock_code in enumerate(self.stock_codes):
            ibconn.reqMktData(i
                              , self.positions_dict[stock_code].tradable
                              , DataType.GENERIC_TICKS_NONE
                              , DataType.SNAPSHOT_NONE)
            time.sleep(1)

    def request_account_updates(self, ibconn):
        ibconn.reqAccountUpdates(True, self.account_code)
        time.sleep(1)

    def cancel_market_data_request(self, ibconn):
        for i in range(len(self.stock_codes)):
            ibconn.cancelMktData(i)
            time.sleep(1)

    def init_context(self, codes):
        self.stock_codes = codes
        self.stock_ticks_dict = dict([(stock_code, StockTick()) for stock_code in self.stock_codes])
        self.positions_dict = dict([(stock_code, StockPosition(stock_code)) for stock_code in self.stock_codes])

    def setup_connection(self):
        return Connection.create(port=4001, clientId=101) if self.is_use_gateway else ibConnection()

    @staticmethod
    def disconnect(ibconn):
        ibconn.disconnect()

    def set_connection_with_api_gateway(self, is_use_api_gateway):
        self.is_use_gateway = is_use_api_gateway

    def request_historical_data(self, ibconn, duration, interval):
        for i, stock_code in enumerate(self.positions_dict):
            ibconn.reqHistoricalData(i
                                     , self.positions_dict[stock_code].tradable
                                     , strftime(DataType.DATE_TIME_FORMAT)
                                     , duration
                                     , interval
                                     , DataType.WHAT_TO_SHOW_TRADES
                                     , DataType.RTH_ALL
                                     , DataType.DATEFORMAT_STRING)
            time.sleep(1)

    def start_historical_data_stream(self
                                     , stock_codes_arr
                                     , duration=DataType.DURATION_1_DAY
                                     , interval=DataType.BAR_SIZE_1_MIN
                                     , handler_func=None):
        self.init_context(stock_codes_arr)

        self.on_historical_data_func = handler_func

        self.conn = self.setup_connection()
        self.is_shutdown = False

        try:
            self.register_event_handlers(self.conn)
            self.conn.connect()
            self.request_historical_data(self.conn, duration, interval)

            while not self.is_shutdown:
                time.sleep(1)

        except Exception, e:
            print "Err: ", e
            print "Disconnecting..."
            self.conn.disconnect()
            time.sleep(1)
            print "Disconnected."

    def assign_functions(self, func_a, func_b):
        self.on_position_changed_func = func_a
        self.on_tick_func = func_b

    def start_data_stream(self
                          , on_started_func
                          , on_tick
                          , stock_codes_to_stream
                          , on_pos_changed=None):

        self.init_context(stock_codes_to_stream)
        self.assign_functions(on_pos_changed, on_tick)

        self.conn = self.setup_connection()

        try:
            self.register_event_handlers(self.conn)
            self.conn.connect()
            self.request_streaming_data(self.conn)
            self.request_account_updates(self.conn)
            on_started_func()

        except Exception, e:
            print "Err: ", e

            print "Cancelling...",

            self.cancel_market_data_request(self.conn)

            print "Disconnecting..."
            self.disconnect(self.conn)
            time.sleep(1)

            print "Disconnected."