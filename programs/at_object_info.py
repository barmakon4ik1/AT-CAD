# -*- coding: utf-8 -*-
# programs/at_object_info.py
import time
import pywintypes
import wx
import pythoncom
from config.at_cad_init import ATCadInit
from windows.at_entity_inspector import show_entity_inspector


def variant_to_list(value):
    try:
        return list(value)
    except ValueError:
        return value

# ---------------------------------------------------------
# AutoCAD selection
# ---------------------------------------------------------

def select_single_object(doc):

    sel_name = "PY_TMP_SEL"

    try:
        doc.SelectionSets.Item(sel_name).Delete()
    except:
        pass

    sel = doc.SelectionSets.Add(sel_name)

    print("Выберите объект в AutoCAD...")
    sel.SelectOnScreen()

    def com_retry(func, retries=10, delay=0.1):

        for _ in range(retries):
            try:
                return func()
            except pywintypes.com_error as e:
                if e.args[0] == -2147418111:
                    time.sleep(delay)
                    continue
                raise

        raise RuntimeError("AutoCAD COM не отвечает")

    count = com_retry(lambda: sel.Count)
    obj = com_retry(lambda: sel.Item(0))

    print("Количество выбранных объектов:", count)

    for i in range(count):
        o = sel.Item(i)
        print(f"Index {i}: {o.ObjectName}, Handle={o.Handle}")

    return obj

# ---------------------------------------------------------
# Entity inspector
# ---------------------------------------------------------

def dump_entity(obj):

    lines = ["=== ОСНОВНЫЕ СВОЙСТВА ==="]

    base_props = [
        "ObjectName",
        "Layer",
        "Linetype",
        "LinetypeScale",
        "Lineweight",
        "Color",
        "Handle",
        "Visible"
    ]

    for p in base_props:
        try:
            lines.append(f"{p}: {getattr(obj, p)}")
        except:
            pass

    lines.append("\n=== ГЕОМЕТРИЯ ===")

    name = obj.ObjectName

    try:

        if name == "AcDbPolyline":

            coords = variant_to_list(obj.Coordinates)

            vertex_count = len(coords) // 2

            lines.append(f"VertexCount: {vertex_count}")
            lines.append(f"Length: {round(obj.Length,3)} мм")
            lines.append(f"Area: {round(getattr(obj,'Area',0),3) / 1000000} м²")

    except Exception as e:
        lines.append(f"Ошибка геометрии: {e}")

    return lines


# def show_entity_window(obj):
#
#     app = wx.GetApp()
#
#     created_here = False
#
#     if app is None:
#         app = wx.App(False)
#         created_here = True
#
#     frame = EntityInspectorFrame(obj)
#     frame.Show()
#
#     if created_here:
#         app.MainLoop()

# ---------------------------------------------------------
# main
# ---------------------------------------------------------
def object_properties(document):
    """
    Вывод свойств объекта в окне
    Args:
        document: документ автокад
    Returns:
        всплывающее окно со свойствами
    """
    obj = select_single_object(document)
    if obj:
        show_entity_inspector(None)

def object_dump(document):
    obj = select_single_object(document)
    lines = dump_entity(obj)
    for line in lines:
        print(line)


def get_object_properties():
    pythoncom.CoInitialize()
    acad = ATCadInit()
    doc = acad.document
    while True:
        cmd = input(
            "\n1-Показать в окне свойства объекта\n"
            "2-Вывести основные свойства объекта в консоль\n"
            "другое - выход\n"
        )
        if cmd == "2":
            object_dump(doc)
        elif cmd == "1":
            object_properties(doc)
        else:
            return


if __name__ == "__main__":
    get_object_properties()