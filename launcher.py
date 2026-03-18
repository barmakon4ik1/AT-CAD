import sys
from pathlib import Path
import importlib.util
import wx

# --- базовая папка ---
BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


def load_ATMainWindow():
    path = BASE_DIR / "windows" / "at_main_window.py"
    spec = importlib.util.spec_from_file_location("at_main_window", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ATMainWindow


def run():
    ATMainWindow = load_ATMainWindow()

    app = wx.App()
    app.SetAppDisplayName("AT-CAD")
    app.SetVendorName("YourCompany")  # можно убрать

    window = ATMainWindow()

    # --- Иконка ---
    icon_path = BASE_DIR / "AT-CAD.ico"
    if icon_path.exists():
        icon = wx.Icon(str(icon_path), wx.BITMAP_TYPE_ICO)
        window.SetIcon(icon)

    window.Show()
    app.MainLoop()


if __name__ == "__main__":
    run()