import logging
import os
import ta.trend

from time import sleep
from bot.bb import FuturesOrders

logger = logging.getLogger('deadmix57')

class Bot(FuturesOrders):
    """
    Класс Bot реализует логику торговли,
    а методы взаимодествия с биржей наследуются из класса.
    Можно наследоваться от класса где будет реализовано взаимодействие
    с др биржей, или с др типами оредеров (например фьючерсы)
    """

    def __init__(self):
        super(Bot, self).__init__()
        # загрузка значения из переменных окружения,
        # чтобы при изменении окружения после запуска бота,
        # бот продолжал нормально работать
        self.timeout = int(os.getenv('TIMEOUT', 30))
        self.timeframe = os.getenv('TIMEFRAME', '240')
        self.macd_fast = int(os.getenv('MACD_FAST', '12'))
        self.macd_slow = int(os.getenv('MACD_SLOW', '26'))
        self.symbol = os.getenv('SYMBOL')

    def is_cross(self):
        """
        Определяю пересечение 12 и 26 скользящих по MACD
        Возвращает:
         0 - если на текущем баре пересечения нет
         1 - быстрая пересекает медленную снизу вверх, пересечение, сигнал на покупку
        -1 - быстрая пересекает медленную снизу вверх, пересечение, сигнал на продажу
        """
        # Серия Пандас с ценами закрытия, в обратном порядке
        close = self.get_close_prices()

        # Расчет скользящих средних,
        # более свежие значение в конце списка
        # нужны 2 последних значения
        macd_obj = ta.trend.MACD(
            close,
            window_slow=self.macd_slow,
            window_fast=self.macd_fast,
            window_sign=9,
            fillna=True
        )
        macd = macd_obj.macd().values
        macd_signal = macd_obj.macd_signal().values

        r = 0
        if macd[-1] > macd_signal[-1] and macd[-2] < macd_signal[-2]: r = 1 # пересечение, быстрая снизу вверх
        elif macd[-1] < macd_signal[-1] and macd[-2] > macd_signal[-2]: r =-1 # пересечение, быстрая свверху вниз

        if r != 0:
            logger.info(f"{r} = now {macd[-1]:.6f} / {macd_signal[-1]:.6f}, prev {macd[-2]:.6f} / {macd_signal[-2]:.6f}")
        return r

    def check(self):
        """
        Проверка сигналов и постановка ордеров
        """
        try:
            cross = self.is_cross()

            if cross > 0 and not self.get_positions():
                self.place_market_order_by_base(0.001, 'Buy')
            elif cross < 0 and self.get_positions():
                self.place_market_order_by_base(0.001, 'Sell')

        except Exception as e:
            logger.error(str(e))

    def loop(self):
        """
        Цикл проверки
        """
        while True:
            self.check()
            sleep(self.timeout)

    def run(self):
        """
        Инициализация бота
        """
        logger.info("Бот запущен!")
        self.check_permissions()

        # Можно запускать вечный цикл, если бот локально
        self.loop()
        # Для Яндекс Cloud Functions по триггеру
        # self.check()