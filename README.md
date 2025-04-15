Алгоритмический бот для торговли фьючерсами на криптовалютной бирже Bybit.
Бот использует библиотеку pybit для работы с API биржи, и библиотеку Pandas для работы с 
полученными данными. Для расчета логики бота используется библиотека ta.
Вся торговая логика находится в файле 'bb.py', логика самого бота в файле 'Bot.py'.
Бот находится на этапе разработки. В дальнейшем планируется ввести функционал по 
выставлению стоп-ордеров, осо-ордеров, изменению торгового плеча. 
Так же планирую связать бота с телеграм ботом, для отправки пуш-уведомлений 
об изменениях по позициям с помощью вебсокетов. 

Глобально есть планы обучать это бот с помощью библиотеки Scikit-Learn, чтобы сделать из него 
полноценный автоматизированный инструмент для пассивного заработка на криптовалютном рынке.
