# windows/flange_window.py (отрывок)
import wx
from programs.flange_models import db, Flange

class FlangeWindow(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.choice_std = wx.Choice(self)
        self.choice_type = wx.Choice(self)
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT)
        self.list.InsertColumn(0, "NPS")
        self.list.InsertColumn(1, "D")
        self.list.InsertColumn(2, "T")

        self.load_standards()
        self.choice_std.Bind(wx.EVT_CHOICE, self.on_std)
        self.choice_type.Bind(wx.EVT_CHOICE, self.on_type)

    def load_standards(self):
        db.connect(reuse_if_open=True)
        q = Flange.select(Flange.standard).distinct()
        items = [r.standard for r in q]
        self.choice_std.SetItems(items)

    def on_std(self, event):
        std = self.choice_std.GetStringSelection()
        q = Flange.select(Flange.type).where(Flange.standard == std).distinct()
        types = [r.type for r in q]
        self.choice_type.SetItems(types)

    def on_type(self, event):
        std = self.choice_std.GetStringSelection()
        ftype = self.choice_type.GetStringSelection()
        rows = Flange.select().where((Flange.standard==std)&(Flange.type==ftype))
        self.list.DeleteAllItems()
        for f in rows:
            idx = self.list.InsertItem(self.list.GetItemCount(), f.nps)
            self.list.SetItem(idx, 1, str(f.D or ''))
            self.list.SetItem(idx, 2, str(f.T or ''))
