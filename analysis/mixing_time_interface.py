"""

Created by: Nathan Starkweather
Created on: 11/24/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

import tkinter as tk
import tkinter.ttk as ttk

from hello.hello import HelloApp
from hello import logger

_logger = logger.BuiltinLogger(__name__)
_info = _logger.info
_debug = _logger.debug


class SimpleMenu(ttk.OptionMenu):
    def __init__(self, master, command, initvalue, options):
        self.var = tk.StringVar(None, initvalue)
        ttk.OptionMenu.__init__(self, master, self.var, None, command=command, *options)

    def get(self):
        return self.var.get()

    def grid(self, row, col, **kw):
        ttk.OptionMenu.grid(self, row=row, column=col, **kw)


class ItemButton(ttk.Button):
    def __init__(self, master, name, cmd, **kw):
        self.tv = tk.StringVar(None, name)
        super().__init__(master, textvariable=self.tv, command=cmd, **kw)

    def grid(self, row, col, **kwargs):
        super().grid(row=row, column=col, **kwargs)


class StatefulItemButton(ItemButton):
    def __init__(self, master, name, initial_cmd):
        super().__init__(master, name, self._do_cmd)
        self._cmd = initial_cmd

    def _do_cmd(self, *args, **kwargs):
        self._cmd(*args, **kwargs)

    def set_cmd(self, cmd):
        self._cmd = cmd


class SimpleEntryButton():
    def __init__(self, root, frame_text, button_text, button_cmd):
        self.frame = ttk.Frame(root)
        self.label = ttk.Label(self.frame, text=frame_text)
        self.entry_tv = tk.StringVar()
        self.entry = ttk.Entry(self.frame, textvariable=self.entry_tv)
        self.button = StatefulItemButton(self.frame, button_text, button_cmd)

    def grid(self, row, col):
        self.frame.grid(row=row, column=col, rowspan=2, sticky=tk.N)
        self.entry.grid(row=1, column=1, columnspan=1)
        self.button.grid(1, 2)
        self.label.grid(row=0, column=1, sticky=tk.W)

    def grid_forget(self):
        for w in (self.frame, self.entry, self.button, self.label):
            w.grid_forget()

    def get_entry_text(self):
        return self.entry_tv.get()


class SimpleListbox():
    def __init__(self, root, label_text):
        self.frame = ttk.Frame(root)
        self.label = ttk.Label(root, text=label_text)
        self.listbox = tk.Listbox(root)

    def grid(self, row, col):
        _debug("Gridding")
        self.frame.grid(row=row, column=col)
        self.label.grid(row=0, column=0)
        self.listbox.grid(row=1, column=0)

    def grid_forget(self):
        for w in (self.frame, self.label, self.listbox):
            w.grid_forget()

    def insert(self, index, items):
        self.listbox.insert(index, *items)

    def delete(self, first, last):
        self.listbox.delete(first, last)

    def clear(self):
        self.delete(0, tk.END)


class IPAddyFrameView():
    def __init__(self, root):
        self.frame = ttk.LabelFrame(root, text="Open by IP Address")
        self.batch_listbox = SimpleListbox(self.frame, "Batch List:")
        self.gb_frame = SimpleEntryButton(self.frame, "Enter IP Address:", "get Batches!", self._do_gb_cb)

    def _do_gb_cb(self):
        self.getbatches_btn_cb()

    def getbatches_btn_cb(self):
        pass  # hook

    def insert_batches(self, names):
        _debug("Inserting %s names", len(names) if hasattr(names, "__len__") else "??")
        self.batch_listbox.insert(tk.END, names)

    def clear_batches(self):
        _debug("Clearing all batches")
        self.batch_listbox.clear()

    def grid(self, row, col):
        _debug("Gridding %s" % self.__class__.__name__)
        self.frame.grid(row=row, column=col)
        self.batch_listbox.grid(0, 0)
        self.gb_frame.grid(0, 1)

    def grid_forget(self):
        self.gb_frame.grid_forget()
        self.batch_listbox.grid_forget()
        self.frame.grid_forget()

    def get_ipv4(self):
        return self.gb_frame.get_entry_text()


class IPAddyFrameModel():
    def __init__(self):
        self._batch_list = None

    def get_batches(self, ipv4):
        _debug("Getting batches from %s", ipv4)
        app = HelloApp(ipv4)
        batches = app.getBatches()
        self._batch_list = batches
        return batches


class IPAddyFrameWidget():
    def __init__(self, root, autogrid=True):

        # create model/view
        self.view = IPAddyFrameView(root)
        self.model = IPAddyFrameModel()

        # configure view callbacks
        self.view.getbatches_btn_cb = self.get_batches

        if autogrid:
            self.view.grid(0, 0)

    def get_batches(self):
        _debug("callback called")
        ipv4 = self.view.get_ipv4()
        batches = self.model.get_batches(ipv4)
        self.view.clear_batches()
        self.view.insert_batches(b.name for b in batches.ids_to_batches.values())

    def grid(self, row, col):
        self.view.grid(row, col)

    def grid_forget(self):
        self.view.grid_forget()


class FilenameFrameView():
    def __init__(self, root):
        self.frame = ttk.LabelFrame(root)
        self.listbox = SimpleListbox(self.frame, "Batch List:")
        self.browse = StatefulItemButton(self.frame, "Browse", self.browse_btn_cb)

    def browse_btn_cb(self):
        pass  # hook

    def grid(self, row, col):
        self.frame.grid(row=row, column=col)
        self.listbox.grid(0, 0)
        self.browse.grid(2, 0, sticky=tk.E)


class FilenameFrameModel():
    def __init__(self, root):
        pass


class FilenameFrameWidget():
    def __init__(self, root):
        self.view = FilenameFrameView(root)
        self.model = FilenameFrameModel(root)

    def grid(self, row, col):
        self.view.grid(row, col)

    def grid_forget(self):
        self.view.grid_forget()


class MixingTimeInterface():
    str_by_ip = "By IP"
    str_by_fn = "By Filename"

    def __init__(self):
        self.root = tk.Tk()
        self.active_frame = None
        ip_frame = IPAddyFrameWidget(self.root)
        fn_frame = FilenameFrameWidget(self.root)

        self.name_to_frames = {
            self.str_by_ip: ip_frame,
            self.str_by_fn: fn_frame
        }
        self.frames_to_names = {v: k for v, k in self.name_to_frames.items()}

        self.menubutton = SimpleMenu(self.root, self.on_menu_change,
                                     self.str_by_ip, [self.str_by_ip, self.str_by_fn])
        self.activate_frame(ip_frame)
        self.menubutton.grid(0, 0, sticky=tk.W)

    def mainloop(self):
        _debug("Beginning mainloop")
        self.root.mainloop()

    def activate_frame(self, ip_frame):
        if self.active_frame:
            self.active_frame.grid_forget()
        self.active_frame = ip_frame
        self.root.grid()
        self.active_frame.grid(1, 0)

    def on_menu_change(self, txt):
        if self.name_to_frames[txt] != self.active_frame:
            self.activate_frame(self.name_to_frames[txt])


if __name__ == '__main__':
    m = MixingTimeInterface()
    m.active_frame.view.gb_frame.entry_tv.set("192.168.1.7")
    m.mainloop()
