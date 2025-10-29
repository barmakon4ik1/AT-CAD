"""
Файл: programs/lisp_bridge.py

Описание:
Модуль взаимодействия Python ↔ AutoLISP без использования COM.
Позволяет обмениваться данными между AutoCAD и Python через временные JSON-файлы.

Принцип работы:
1. Python записывает запрос в JSON-файл (например, "get_point", "get_entity").
2. AutoLISP выполняет соответствующий .lsp-файл, получает результат (точку, объект).
3. LISP записывает результат обратно в JSON.
4. Python ждёт и считывает ответ.

Работает надёжно и независимо от COM API.
"""

import json
import os
import time
from typing import Any, Dict, Optional


# -----------------------------
# Константы
# -----------------------------
BRIDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "lisp_bridge")
REQ_FILE = os.path.join(BRIDGE_DIR, "request.json")
RES_FILE = os.path.join(BRIDGE_DIR, "response.json")


# -----------------------------
# Утилиты
# -----------------------------
def ensure_bridge_dir():
    """Создаёт директорию обмена, если она отсутствует."""
    if not os.path.exists(BRIDGE_DIR):
        os.makedirs(BRIDGE_DIR, exist_ok=True)


def write_request(data: Dict[str, Any]) -> None:
    """Записывает запрос в JSON."""
    ensure_bridge_dir()
    with open(REQ_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_response(timeout: float = 10.0) -> Optional[Dict[str, Any]]:
    """
    Ожидает ответа от LISP, читает JSON.
    Возвращает None при тайм-ауте.
    """
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(RES_FILE):
            try:
                with open(RES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                os.remove(RES_FILE)
                return data
            except Exception:
                pass
        time.sleep(0.2)
    return None


def send_lisp_command(command: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Универсальная функция: отправляет запрос LISP и ждёт ответа.
    Пример:
        send_lisp_command("get_point", {"prompt": "Укажите точку:"})
    """
    ensure_bridge_dir()
    if os.path.exists(RES_FILE):
        os.remove(RES_FILE)

    data = {"command": command, "params": params or {}}
    write_request(data)

    print(f"[Bridge] Запрос к AutoLISP: {command}")
    result = read_response()
    if not result:
        print("[Bridge] Ответ не получен (тайм-аут).")
    else:
        print(f"[Bridge] Ответ от AutoLISP: {result}")
    return result
