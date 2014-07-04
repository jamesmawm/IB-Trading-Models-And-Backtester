#######################################
# Author: James Ma
# Email stuff here: jamesmawm@gmail.com
#######################################

from ib.ext.Contract import Contract
from ib.ext.Order import Order
import ibDataTypes as DataType


def make_ib_contract(contract_tuple):
    contract = Contract()
    contract.m_symbol = contract_tuple[0]
    contract.m_secType = contract_tuple[1]
    contract.m_exchange = contract_tuple[2]
    contract.m_currency = contract_tuple[3]
    contract.m_expiry = contract_tuple[4]
    contract.m_strike = contract_tuple[5]
    contract.m_right = contract_tuple[6]
    return contract


def create_stock_contract(stock):
    contract_tuple = (stock, 'STK', 'SMART', 'USD', '', 0.0, '')
    stock_contract = make_ib_contract(contract_tuple)
    return stock_contract


def create_stock_order(order_id, quantity, is_buy, price=None, stop_price=None):
    order = Order()

    order.m_outsideRth = True
    order.m_orderId = order_id
    order.m_totalQuantity = quantity
    order.m_action = DataType.ORDER_ACTION_BUY if is_buy else DataType.ORDER_ACTION_SELL

    if price is None:
        order.m_orderType = DataType.ORDER_TYPE_MARKET
    else:
        order.m_lmtPrice = price
        order.m_orderType = DataType.ORDER_TYPE_LIMIT

        if stop_price is not None:
            order.m_auxPrice = stop_price
            order.m_orderType = DataType.ORDER_TYPE_STOP_LIMIT

    return order