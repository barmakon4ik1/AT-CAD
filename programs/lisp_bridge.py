# ================================================================
# Файл: programs/lisp_bridge.py
# Назначение: Мост между Python и AutoCAD LISP через JSON-файлы.
# Работает с единым Lisp-файлом ATC_LISP_BRIDGE.lsp
# ================================================================

import json
import os
import time
import logging
import win32com.client

# ================================================================
# Пути к файлам обмена
# ================================================================
BRIDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "lisp_bridge")
REQ_FILE = os.path.join(BRIDGE_DIR, "request.json")
RES_FILE = os.path.join(BRIDGE_DIR, "response.json")

# ================================================================
# Служебные функции
# ================================================================
def ensure_bridge_dir():
    if not os.path.exists(BRIDGE_DIR):
        os.makedirs(BRIDGE_DIR, exist_ok=True)

def write_request(data):
    ensure_bridge_dir()
    with open(REQ_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if os.path.exists(RES_FILE):
        try:
            os.remove(RES_FILE)
        except Exception:
            pass

def read_response(timeout: float = 8.0):
    """Ожидает появления response.json до тайм-аута."""
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(RES_FILE):
            try:
                with open(RES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                try:
                    os.remove(RES_FILE)
                except Exception:
                    pass
                return data
            except Exception as e:
                logging.warning(f"[Bridge] Ошибка чтения response.json: {e}")
        time.sleep(0.15)
    return None

# ================================================================
# Основная функция вызова
# ================================================================
def send_lisp_command(command: str, params: dict = None, timeout: float = 8.0):
    """
    Передаёт команду в AutoCAD через JSON и вызывает (ATC_PROCESS_REQUEST)
    из единого модуля ATC_LISP_BRIDGE.lsp.
    """
    ensure_bridge_dir()
    payload = {"command": command, "params": params or {}}
    write_request(payload)

    try:
        acad = win32com.client.GetActiveObject("AutoCAD.Application")
        doc = acad.ActiveDocument
        # ★ Вызов теперь единый — (ATC_PROCESS_REQUEST)
        doc.SendCommand("(ATC_PROCESS_REQUEST)\n")
    except Exception as e:
        logging.warning(f"[Bridge] Не удалось вызвать AutoCAD.SendCommand: {e}")
        print(f"[Bridge] Ошибка при обращении к AutoCAD: {e}")
        print("→ Проверьте, что ATC_LISP_BRIDGE.lsp загружен в AutoCAD.")

    res = read_response(timeout=timeout)
    if not res:
        logging.warning("[Bridge] Ответ от AutoCAD не получен (тайм-аут).")
    return res

# ================================================================
# Дополнительные функции
# ================================================================
def ensure_lisp_loaded():
    """
    Проверяет, загружен ли Lisp-модуль.
    Можно использовать (atc_ping) или (ATC_LOAD_LISP) для загрузки вручную.
    """
    logging.debug("[Bridge] Проверка загрузки Lisp-модуля...")
    try:
        res = send_lisp_command("ping")
        if res and res.get("status") == "ok":
            logging.info("[Bridge] LISP-модуль активен.")
            return True
        # если нет, попробуем вручную вызвать загрузку
        acad = win32com.client.GetActiveObject("AutoCAD.Application")
        doc = acad.ActiveDocument
        # ★ Загрузка выполняется единым Lisp-файлом, без разных функций
        doc.SendCommand('(ATC_LOAD_LISP_BRIDGE)\n')
        res = read_response(timeout=3.0)
        return bool(res)
    except Exception as e:
        logging.warning(f"[Bridge] ensure_lisp_loaded: {e}")
        return False

def ping():
    """Проверяет доступность Lisp-моста."""
    try:
        res = send_lisp_command("ping")
        if res and res.get("status") == "ok":
            return True
    except Exception as e:
        logging.debug(f"[Bridge] ping error: {e}")
    return False

# ================================================================
# Прямой тест
# ================================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("=== Тест LISP-моста ===")
    print("→ Проверка ping:", ping())
    print("→ Проверка загрузки LISP:", ensure_lisp_loaded())
    print("→ Попытка вызвать get_point...")
    res = send_lisp_command("get_point")
    print("Ответ:", res)
