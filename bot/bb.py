import logging
import decimal
import inspect
import os
import time
import pandas as pd

from typing import Optional

from pybit import exceptions
from pybit.unified_trading import WebSocket, HTTP

logger = logging.getLogger('deadmix57')

class FuturesOrders:
    def __init__(self):
        logger.info(f'{os.getenv('NAME', 'deadmix57')} bybit loaded')
        '''
        Конструктор класса и инициализация
        - клиента bybit
        - получение параметров и фильтров инструмента
        '''
        self.cl = HTTP(
            testnet=os.getenv('IS_TESTNET', 'True'),
            api_key=os.getenv('API_KEY', '1'),
            api_secret=os.getenv('SECRET', '1')
        )
        self.symbol = os.getenv('SYMBOL')
        self.category = 'linear'
        # Вот здесь вызывается функция класса по фильтрам инструмента
        self.price_decimals, self.qty_decimals, self.min_qty = self.get_filters()

    def check_permissions(self, accountType: str = 'UNIFIED'):
        '''Запрос к состоянию баланса аккаунта
       для проверки прав доступа ключей,
       если ключи не правильные выкинет ошибку
       '''
        r = self.cl.get_wallet_balance(accountType=accountType)

    def get_filters(self):
        '''
        Фильтры заданного инструмента
        - макс кол-во знаков в аргументах цены,
        - мин размер ордера в Базовой валюте,
        - макс размер ордера в БВ
        '''
        r = self.cl.get_instruments_info(symbol=self.symbol, category=self.category)
        c = r.get('result', {}).get('list', [])[0]

        min_qty = c.get('lotSizeFilter', {}).get('minOrderQty', '0.0')
        qty_decimals = abs(decimal.Decimal(min_qty).as_tuple().exponent)
        price_decimals = int(c.get('priceScale', '4'))
        min_qty = float(min_qty)

        self.log(price_decimals, qty_decimals, min_qty)
        return price_decimals, qty_decimals, min_qty

    def get_close_prices(self, interval: str = '240', limit: int = 10):
        '''
        Получение цены закрытия последних свечей
        '''
        r = self.cl.get_kline(
            category=self.category,
            symbol=self.symbol,
            interval=interval,
            limit=limit
        ).get('result').get('list')
        r.reverse()
        return pd.Series([float(e[4]) for e in r])

    def get_price(self):
        '''
        Получение текущей цены
        '''
        r = float(self.cl.get_tickers(
            category=self.category,
            symbol=self.symbol).get('result').get('list')[0].get('ask1Price')
        )
        self.log(r)
        return r

    def get_positions(self, key: Optional[str] = None):
        '''
        Получение текущей позиции
        :param key:
        :return:
        '''
        r = self.cl.get_positions(category=self.category, symbol=self.symbol)
        p = r.get('result', {}).get('list', [])[0]
        qty = float(p.get('size', '0.0'))
        if qty<= 0.0: raise Exception('empty position')

        ret = dict(
            avg_price=float(p.get('avgPrice', '0.0')),
            side=p.get('side'),
            unrel_pnl=float(p.get('unrealisedPnl', '0.0')),
            qty=qty
        )
        ret['rev_side'] = ('Sell', 'Buy')[ret['side'] == 'Sell']
        self.log(ret)

        return ret.get(key) if key else ret

    # def is_position(self):
    #     '''
    #     Проверка, открыта ли какая либо позиция ботом
    #     '''
    #     ret = self.get_positions()
    #
    #     for o in ret:
    #         if o.get('order_link_id') != self.order_link_id: continue
    #         return o.get('side') == 'buy'
    #     return False

    def place_limit_order_by_pecent(
            self,
            qty: float = 0.00001,
            side: str = 'Sell',
            distance_perc: int = 2,
            order_link_id: Optional[str] = None
    ):
        '''
        Установка лимитного ордера по инструменту определенному в конструкторе класса
        в процентах от текущей цены
        в зависимости от направления лимитного ордера цена стопа расчитывается в разные стороны
        '''
        current_price = self.get_price()
        order_price = self.calculate_limit_price_perc(current_price, side, distance_perc)
        if not order_link_id: order_link_id = f'deadmix_{self.symbol}_{time.time()}'

        args = dict(
            category=self.category,
            symbol=self.symbol,
            side=side.capitalize(),
            orderType='Limit',
            qty=self.floor_qty(qty),
            price=self.floor_price(order_price),
            order_link_id=order_link_id
        )
        self.log('args', args)

        r = self.cl.place_order(**args)
        self.log('result', r)

        return r

    def place_market_order_by_base(self, qty: float = 0.00001, side: str = 'Sell'):
        '''
        Размещение рыночного ордера с указанием размера ордера в Базовой Валюте (BTC, XRP, etc)
        '''
        args = dict(
            category=self.category,
            symbol=self.symbol,
            side=side.capitalize(),
            orderType="Market",
            qty=self.floor_qty(qty),
            orderLinkId=f"deadmix_{self.symbol}_{time.time()}"
        )
        self.log("args", args)

        r = self.cl.place_order(**args)
        self.log("result", r)

        return r

    def place_market_order_by_quote(self, quote: float = 5.0, side: str = "Sell"):
        """
        Отправка ордера с размером позиции в Котируемой Валюте (USDT напр)
        имеет смысл только для контрактов
        """
        curr_price = self.get_price()
        qty = self.floor_qty(quote / curr_price)
        if qty < self.min_qty: raise Exception(f"{qty} is to small")

        self.place_market_order_by_base(qty, side)

    def cancel_open_order_by_order_link_id(self, order_link_id):
        '''
        Отмена ордера по идентификатору
        '''
        r = self.cl.cancel_order(
            category=self.category,
            symbol=self.symbol,
            orderLinkId=order_link_id
        )
        self.log(r)

        return r

    def cancel_all_open_orders(self):
        '''
        Отмена всех открытых позиций
        '''
        r = self.cl.cancel_all_orders(category=self.category, symbol=self.symbol)
        print('Все ордера отменены', r)

    def reverse_position(self):
        """
        Переворот позиции
        """
        p = self.get_positions()
        return self.place_market_order_by_base(p['qty'] * 2, p['rev_side'])

    def close_position(self):
        '''
        Полное закрытие позиции
        '''
        args = dict(
            category=self.category,
            symbol=self.symbol,
            side=self.get_positions("rev_side"),
            orderType="Market",
            qty=0.0,
            orderLinkId=f"deadmix_{self.symbol}_{time.time()}",
            reduceOnly=True,
            closeOnTrigger=True,
        )
        self.log('args', args)

        r = self.cl.place_order(**args)
        self.log('result', r)

    def place_conditional_order(
            self,
            qty: float,
            side: str,
            trigger_price: float,
            order_price: Optional[float] = None,
    ):
        '''
        Размещение Conditional Order
        '''
        current_price = self.get_price()

        args = dict(
            category=self.category,
            symbol=self.symbol,
            side=side.capitalize(),
            qty=self.floor_qty(qty),

            orderType="Limit",
            price=self.floor_price(order_price),

            triggerPrice=self.floor_price(trigger_price),
            triggerDirection=1 if trigger_price > current_price else 2,
        )
        self.log('args', args)

        r = self.cl.place_order(**args)
        self.log('result', r)

        return r

    # def place_stop_loss(self, perc: float = 5):
    #     ...
    #
    # def place_take_profit(self, perc: float = 5):
    #     ...
    #
    # def place_oco_order(self):
    #     ...
    #
    # def set_leverage(self):
    #     ...

    def log(self, *args):
        '''
        Для удобного вывода из методов класса
        '''
        caller = inspect.stack()[1].function
        print(f'* {caller}', self.symbol, '\n\t', args, '\n')

    def _floor(self, value, decimals):
        '''
        Для аргументов цены нужно отбросить (округлить вниз)
        до колва знаков заданных в фильтрах цены
        !!Переработать с использованием библиотеки decimal!!
        '''
        factor = 1 / (10 ** decimals)
        return (value // factor) * factor

    def floor_price(self, value):
        return self._floor(value, self.price_decimals)

    def floor_qty(self, value):
        return self._floor(value, self.qty_decimals)

    def calculate_limit_price_perc(self, price, side: str = 'Sell', distance_perc: int = 2):
        '''
        Расчет цен для постановки лимитного ордера
        в процентах от заданной цены
        и в зависимости от направления
        '''
        return price * (100 + ((-1, 1)[side.lower() == 'sell'] * distance_perc)) / 100
