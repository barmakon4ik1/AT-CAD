"""
logging_setup.py
================

Централизованная настройка логирования приложения K-Finder.

Назначение
----------
В старой версии логгер создавался прямо внутри большого файла GUI-модуля.
Теперь логирование вынесено в отдельный модуль, чтобы:

- не дублировать настройку logger в разных файлах;
- всегда писать лог в data/kfinder.log;
- безопасно использовать один и тот же logger из всех модулей проекта;
- не вмешиваться в root logger и не ломать логирование других приложений.

Что предоставляет модуль
------------------------
1. setup_logging()
   Настраивает logger "kfinder" один раз.

2. get_logger()
   Возвращает готовый logger "kfinder".

Принципы
--------
- Логируем в файл.
- По умолчанию уровень: ERROR.
- logger.propagate = False, чтобы записи не улетали выше по иерархии.
- Если файл лога недоступен, приложение не должно падать.

Важно
-----
Этот модуль не должен импортировать GUI и бизнес-логику.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .paths import LOG_FILE


LOGGER_NAME = "kfinder"


def setup_logging(log_file: Path | None = None, level: int = logging.ERROR) -> logging.Logger:
    """
    Создаёт и настраивает именованный logger приложения.

    Параметры:
    ----------
    log_file:
        Путь к лог-файлу. Если не передан, используется data/kfinder.log.

    level:
        Уровень логирования. По умолчанию ERROR.

    Поведение:
    ----------
    - Если logger уже настроен, повторно handler не добавляется.
    - Если папка под лог не существует, она будет создана.
    - Если файл лога недоступен, logger всё равно возвращается,
      просто без файлового handler-а.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        return logger

    target = log_file or LOG_FILE

    try:
        target.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(target, encoding="utf-8")
        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )

        logger.addHandler(handler)

    except OSError:
        # Лог недоступен — приложение продолжает работать без файла лога.
        pass

    return logger


def get_logger() -> logging.Logger:
    """
    Возвращает logger приложения.

    Если logger ещё не был настроен, выполняется setup_logging()
    с параметрами по умолчанию.
    """
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        return setup_logging()
    return logger