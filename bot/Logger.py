import logging

def setup_logger():
    """
    Чтобы при деплое легко переключить сохранение логов файл
    """
    fmt = logging.Formatter(fmt="%(asctime)s %(levelname).3s | %(message)s", datefmt="%m/%d %H:%M:%S")
    cons = logging.StreamHandler()
    cons.setFormatter(fmt)
    logger = logging.getLogger('deadmix57')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(cons)
    return logger