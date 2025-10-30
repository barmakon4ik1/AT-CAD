# вставьте в programs/lisp_bridge.py (заменяет старую send_lisp_command)
import json, os, time
import win32com.client

BRIDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "lisp_bridge")
REQ_FILE = os.path.join(BRIDGE_DIR, "request.json")
RES_FILE = os.path.join(BRIDGE_DIR, "response.json")

def ensure_bridge_dir():
    if not os.path.exists(BRIDGE_DIR):
        os.makedirs(BRIDGE_DIR, exist_ok=True)

def write_request(data):
    ensure_bridge_dir()
    with open(REQ_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    # remove old response if present
    if os.path.exists(RES_FILE):
        try:
            os.remove(RES_FILE)
        except Exception:
            pass

def read_response(timeout=8.0):
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
            except Exception:
                pass
        time.sleep(0.15)
    return None

def send_lisp_command(command:str, params:dict=None, timeout:float=8.0):
    """
    Записать request.json, вызвать LISP однократно через SendCommand и ждать response.json.
    command: 'get_point' или 'get_entity' (любой текст, который LISP распознает).
    """
    ensure_bridge_dir()
    payload = {"command": command, "params": params or {}}
    write_request(payload)

    # Попытка получить AutoCAD через COM и выполнить SendCommand.
    try:
        acad = win32com.client.GetActiveObject("AutoCAD.Application")
        doc = acad.ActiveDocument
        # Вызываем LISP-обработчик однократно:
        doc.SendCommand("ATC_PROCESS_REQUEST\n")
    except Exception as e:
        # Если COM недоступен, вернуть None — Python не сможет триггерить LISP.
        # Пользователь может запускать команду ATC_PROCESS_REQUEST вручную в AutoCAD.
        print(f"[Bridge] Не удалось вызвать AutoCAD.SendCommand: {e}")

    # ждем ответ
    res = read_response(timeout=timeout)
    if not res:
        print("[Bridge] Ответ не получен (тайм-аут).")
    return res
