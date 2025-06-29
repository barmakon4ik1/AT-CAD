# at_logging.py
"""
Модуль для логирования в проекте AT-CAD.
Поддерживает запись логов в файл и вывод в консоль по настройкам.
"""

import logging
import os
from at_config import LOG_TO_FILE, LOG_TO_CONSOLE, VERBOSE_LOGGING, LOG_FILE_PATH


class AtLogging:
    """
    Класс для управления логированием в проекте с использованием паттерна Singleton.

    Attributes:
        logger: Объект logging.Logger для записи логов.
    """
    _instance = None

    def __new__(cls, log_file=LOG_FILE_PATH, level=logging.DEBUG,
                log_format='%(asctime)s:%(name)s:%(message)s', console_output=LOG_TO_CONSOLE):
        """
        Реализация паттерна Singleton для создания единственного экземпляра логгера.

        Args:
            log_file (str): Путь к файлу логов. По умолчанию из LOG_FILE_PATH.
            level (int): Уровень логирования (по умолчанию DEBUG).
            log_format (str): Формат сообщений логов.
            console_output (bool): Вывод в консоль (по умолчанию из LOG_TO_CONSOLE).

        Returns:
            AtLogging: Единственный экземпляр логгера.
        """
        if cls._instance is None:
            cls._instance = super(AtLogging, cls).__new__(cls)
            cls._instance._initialize(log_file, level, log_format, console_output)
        return cls._instance

    def _initialize(self, log_file, level, log_format, console_output):
        """
        Инициализация логгера с настройкой обработчиков.

        Args:
            log_file (str): Путь к файлу логов.
            level (int): Уровень логирования.
            log_format (str): Формат сообщений.
            console_output (bool): Включить вывод в консоль.
        """
        self.logger = logging.getLogger('AtLogging')
        self.logger.setLevel(level)

        # Удаляем существующие обработчики
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Форматтер для логов
        formatter = logging.Formatter(log_format)

        # Обработчик для файла (все уровни, если LOG_TO_FILE=True)
        if LOG_TO_FILE:
            try:
                log_dir = os.path.dirname(log_file)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir)
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)  # Записываем все уровни
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                print(f"Ошибка настройки файлового лога: {str(e)}")

        # Обработчик для консоли
        if console_output or VERBOSE_LOGGING:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG if VERBOSE_LOGGING else logging.INFO)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def __getattr__(self, name):
        """
        Делегирует вызовы методов (debug, info, error и т.д.) к self.logger.

        Args:
            name (str): Имя метода.

        Returns:
            callable: Метод логгера.
        """
        return getattr(self.logger, name)


def set_verbose_logging(verbose):
    """
    Включает или отключает полное логирование в консоль.

    Args:
        verbose (bool): True для включения, False для отключения.

    Returns:
        AtLogging: Обновленный экземпляр логгера.
    """
    global VERBOSE_LOGGING
    VERBOSE_LOGGING = verbose
    # Пересоздаем логгер для применения новых настроек
    AtLogging._instance = None
    return AtLogging()
