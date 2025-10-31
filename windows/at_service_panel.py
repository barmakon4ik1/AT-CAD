# ================================================================
# Файл: windows/at_service_panel.py
# Назначение:
#   Сервисная панель наблюдения за обменом Python ↔ AutoCAD
#   (исправленная версия: безопасная работа COM и GUI через потоки)
#
# Требования:
#   wxPython, pywin32
#
# Принцип:
#   - Фоновый поток инициализирует pythoncom и только затем пытается
#     получить доступ к AutoCAD через win32com.
#   - Все GUI-операции выполняются через wx.CallAfter (только главный поток).
#   - Любые show_popup() в модулях не должны вызываться из фонового потока.
#     Если модуль может вызывать show_popup, в панели мы передаём
#     suppressed=True (см. рекомендации ниже).
#
# Автор: ChatGPT (адаптирован)
# ================================================================
import win32com.client
import wx
import threading
import time
from datetime import datetime
import pythoncom
import logging

from programs.at_input import at_get_point, at_get_entity


class ATServicePanel(wx.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, title="AT-CAD Service Panel", size=(700, 520))

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Статус
        self.status_static = wx.StaticText(panel, label="Статус: ожидание...")
        font = self.status_static.GetFont()
        font.MakeBold()
        self.status_static.SetFont(font)
        vbox.Add(self.status_static, flag=wx.ALL | wx.EXPAND, border=8)

        # Журнал
        self.log_ctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        vbox.Add(self.log_ctrl, proportion=1, flag=wx.ALL | wx.EXPAND, border=8)

        # Кнопки
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_com_point = wx.Button(panel, label="Точка (COM)")
        self.btn_com_entity = wx.Button(panel, label="Объект (COM)")
        self.btn_bridge_point = wx.Button(panel, label="Точка (Bridge)")
        self.btn_bridge_entity = wx.Button(panel, label="Объект (Bridge)")
        self.btn_clear = wx.Button(panel, label="Очистить журнал")
        self.btn_exit = wx.Button(panel, label="Выход")

        for btn in (
                self.btn_com_point, self.btn_com_entity,
                self.btn_bridge_point, self.btn_bridge_entity,
                self.btn_clear, self.btn_exit
        ):
            hbox.Add(btn, 0, wx.ALL, 5)
        vbox.Add(hbox, flag=wx.ALL | wx.EXPAND, border=5)

        panel.SetSizer(vbox)

        # Bind
        self.btn_com_point.Bind(wx.EVT_BUTTON, lambda evt: self.run_action("COM", "point"))
        self.btn_com_entity.Bind(wx.EVT_BUTTON, lambda evt: self.run_action("COM", "entity"))
        self.btn_bridge_point.Bind(wx.EVT_BUTTON, lambda evt: self.run_action("BRIDGE", "point"))
        self.btn_bridge_entity.Bind(wx.EVT_BUTTON, lambda evt: self.run_action("BRIDGE", "entity"))
        self.btn_clear.Bind(wx.EVT_BUTTON, lambda evt: self.log_ctrl.Clear())
        self.btn_exit.Bind(wx.EVT_BUTTON, lambda evt: self.Close())

        # Поток статуса
        self.keep_running = True
        self.status_thread = threading.Thread(target=self._status_loop, daemon=True)
        self.status_thread.start()

        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.Center()
        self.Show()

    # ------------------------------------------------------------
    def _status_loop(self):
        """
        Фоновая проверка доступности AutoCAD через COM.
        В этом потоке инициализируем pythoncom.
        Результаты (обновление статуса) передаются в GUI через wx.CallAfter.
        """
        try:
            pythoncom.CoInitialize()
        except Exception:
            # если CoInitialize не сработал — всё равно будем пытаться, но логим
            logging.exception("Не удалось CoInitialize в статусном потоке")

        while self.keep_running:
            try:
                # ВНИМАНИЕ: здесь мы не создаём GUI и не вызывает show_popup()
                # Просто проверяем доступность AutoCAD через win32com (GetActiveObject).
                try:
                    import win32com.client
                    acad = win32com.client.GetActiveObject("AutoCAD.Application")
                    # Если получили объект — считаем AutoCAD доступным
                    wx.CallAfter(self.update_status, "AutoCAD доступен (COM активен)", True)
                except Exception:
                    wx.CallAfter(self.update_status, "AutoCAD недоступен", False)
            except Exception:
                # Любая ошибка — обновляем статус как недоступный
                wx.CallAfter(self.update_status, "AutoCAD недоступен (ошибка)", False)

            time.sleep(2.0)

        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    # ------------------------------------------------------------
    def update_status(self, text: str, ok=True):
        """Обновление строки статуса (вызвать только из главного потока или через wx.CallAfter)."""
        self.status_static.SetLabel(f"Статус: {text}")
        self.status_static.SetForegroundColour(wx.Colour(0, 128, 0) if ok else wx.Colour(180, 0, 0))

    # ------------------------------------------------------------
    def log(self, message: str):
        """Добавление записи в журнал (безопасно из главного потока)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_ctrl.AppendText(f"[{timestamp}] {message}\n")

    # ------------------------------------------------------------
    def run_action(self, mode: str, action: str):
        """Запуск теста (создаём рабочий поток)."""
        self.log(f"▶ Тест: {action.upper()} через {mode}")
        thread = threading.Thread(target=self._run_action_thread, args=(mode, action), daemon=True)
        thread.start()

    # ------------------------------------------------------------
    def _run_action_thread(self, mode: str, action: str):
        """
        Фоновый поток: инициализирует COM в своем контексте,
        получает AutoCAD.Application на месте и выполняет всю работу с COM здесь.
        Результат сериализуется и передаётся в GUI через wx.CallAfter.
        """
        import win32com.client
        import pythoncom
        try:
            pythoncom.CoInitialize()
        except Exception:
            logging.exception("CoInitialize failed in worker thread (might be already initialized)")

        try:
            # Попытка получить AutoCAD.Application (несколько попыток для надёжности)
            acad = None
            for attempt in range(3):
                try:
                    acad = win32com.client.GetActiveObject("AutoCAD.Application")
                    break
                except Exception as e:
                    # Если AutoCAD недоступен — ждём немного и пробуем снова
                    logging.debug(f"GetActiveObject attempt {attempt + 1} failed: {e}")
                    time.sleep(0.4)
            if acad is None and mode == "COM":
                wx.CallAfter(self._on_result, "Ошибка: не удалось подключиться к AutoCAD (COM).")
                return

            # Если режим BRIDGE — используем мост (at_get_point/at_get_entity), он не заводит COM-объекты
            if mode == "BRIDGE":
                try:
                    if action == "point":
                        pt = at_get_point(use_bridge=True, as_variant=False, suppress_popups=True)
                        wx.CallAfter(self._on_result, f"Point (Bridge): {pt}")
                    elif action == "entity":
                        ent = at_get_entity(use_bridge=True, suppress_popups=True)
                        wx.CallAfter(self._on_result, f"Entity (Bridge): {ent}")
                    return
                except Exception as e:
                    logging.exception("Bridge call failed")
                    wx.CallAfter(self._on_result, f"Bridge error: {e}")
                    return

            # --- Далее: режим COM, все обращения внутри этого потока ---
            doc = None
            try:
                doc = acad.ActiveDocument
            except Exception as e:
                # Попробуем ещё раз получить ActiveDocument (вдруг документ сменился)
                try:
                    time.sleep(0.2)
                    doc = acad.ActiveDocument
                except Exception as e2:
                    logging.exception("Не удалось получить ActiveDocument")
                    wx.CallAfter(self._on_result, f"Ошибка: не удалось получить ActiveDocument: {e2}")
                    return

            util = getattr(doc, "Utility", None)
            if util is None:
                wx.CallAfter(self._on_result, "Ошибка: Document.Utility недоступен.")
                return

            # Ветвление по действию
            if action == "point":
                try:
                    # Показываем подсказку в командной строке AutoCAD
                    try:
                        util.Prompt("Укажите точку: \n")
                    except Exception:
                        pass
                    # Получаем точку — GetPoint возвращает массив/tuple (x,y[,z])
                    res = util.GetPoint()
                    if not res:
                        wx.CallAfter(self._on_result, "Point (COM): отмена пользователем или ошибка.")
                    else:
                        # Преобразуем в список float
                        pt = list(res)
                        # Обеспечим длину 3
                        while len(pt) < 3:
                            pt.append(0.0)
                        pt = [float(pt[0]), float(pt[1]), float(pt[2])]
                        wx.CallAfter(self._on_result, f"Point (COM): {pt}")
                except Exception as e:
                    logging.exception("Ошибка при GetPoint (COM)")
                    # Попробуем распознать "Objekt not connected" и дать совет по восстановлению
                    hr = getattr(e, "hresult", None)
                    if hr == -2147220995:
                        wx.CallAfter(self._on_result,
                                     "COM: объект не подключён к серверу (перезапустите AutoCAD или переподключитесь).")
                    else:
                        wx.CallAfter(self._on_result, f"Ошибка GetPoint (COM): {e}")

            elif action == "entity":
                try:
                    try:
                        util.Prompt("Выберите объект: \n")
                    except Exception:
                        pass
                    res = util.GetEntity()
                    # GetEntity возвращает (entity, pickPoint)
                    if not res:
                        wx.CallAfter(self._on_result, "Entity (COM): отмена пользователем или ошибка.")
                    else:
                        entity = res[0]
                        pick = res[1] if len(res) > 1 else None
                        # Собираем безопасную сериализуемую информацию (не передаём сам COM-объект)
                        try:
                            obj_info = {
                                "ObjectName": getattr(entity, "ObjectName", str(entity)),
                                "Layer": getattr(entity, "Layer", ""),
                                "Closed": getattr(entity, "Closed", None),
                                "ObjectID": getattr(entity, "ObjectID", None)
                            }
                        except Exception:
                            obj_info = {"ObjectName": str(entity)}
                        # Координаты точки выбора
                        pick_pt = None
                        if pick:
                            try:
                                pick_pt = list(pick)
                                while len(pick_pt) < 3:
                                    pick_pt.append(0.0)
                                pick_pt = [float(pick_pt[0]), float(pick_pt[1]), float(pick_pt[2])]
                            except Exception:
                                pick_pt = None
                        wx.CallAfter(self._on_result, f"Entity (COM): {obj_info}, pick={pick_pt}")
                except Exception as e:
                    logging.exception("Ошибка при GetEntity (COM)")
                    hr = getattr(e, "hresult", None)
                    if hr == -2147220995:
                        wx.CallAfter(self._on_result,
                                     "COM: объект не подключён к серверу (перезапустите AutoCAD или переподключитесь).")
                    elif hr == -2147417842:
                        wx.CallAfter(self._on_result,
                                     "COM: интерфейс маршалирован в другой поток — повторите действие.")
                    else:
                        wx.CallAfter(self._on_result, f"Ошибка GetEntity (COM): {e}")

        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    # ------------------------------------------------------------
    def _on_result(self, text: str):
        """Обработчик результата — вызывается в главном потоке через wx.CallAfter."""
        self.log(text)

    # ------------------------------------------------------------
    def on_close(self, event):
        self.keep_running = False
        self.Destroy()


# ================================================================
if __name__ == "__main__":
    app = wx.App(False)
    frame = ATServicePanel()
    app.MainLoop()
