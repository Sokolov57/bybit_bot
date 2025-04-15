from pybit import exceptions

from bot import Bot
from bot.Logger import setup_logger

from dotenv import load_dotenv

load_dotenv() # чтобы использовать .env рядом с main.py
logger = setup_logger()

if __name__ == '__main__':
    try:
        Bot().run()
    except KeyboardInterrupt as e:
        logger.debug("Бот остановлен вручную")
    except exceptions.InvalidRequestError as e:
        logger.debug(str(e))
    except exceptions.FailedRequestError as e:
        logger.debug(str(e))
    except Exception as e:
        logger.error(str(e))