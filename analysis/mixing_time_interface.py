"""

Created by: Nathan Starkweather
Created on: 11/24/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from hello.hello import HelloApp
import tkinter as tk
import pysrc.mytk as mytk
from pysrc import logger
import threading

_logger = logger.BuiltinLogger(__name__)
_info = _logger.info
_debug = _logger.debug

class IPAddyFrameView():
    def __init__(self, root):
        self.frame = mytk.SimpleLabelFrame(root, text="Open by IP Address")
        self.batch_listbox = mytk.SimpleListbox(self.frame, "Batch List:")
        self.gb_frame = mytk.SimpleEntryButton(self.frame, "Enter IP Address:", "get Batches!", self._do_gb_cb)

    def disable_button(self):
        self.gb_frame.button.config(state=tk.DISABLED)

    def enable_button(self):
        self.gb_frame.button.config(state=tk.NORMAL)

    def _do_gb_cb(self):
        self.getbatches_btn_cb()

    def getbatches_btn_cb(self):
        pass  # hook

    def insert_batches(self, names):
        if not hasattr(names, "__len__"):
            names = tuple(names)
        _debug("Inserting %s names", len(names))
        self.batch_listbox.insert(tk.END, names)

    def insert(self, string):
        self.batch_listbox.insert(tk.END, [string])

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
        app.settimeout(5)
        batches = app.getBatches()
        self._batch_list = batches
        return batches


class IPAddyFrameWidget():
    def __init__(self, root, autogrid=True):

        # create model/view
        self.root = root
        self.view = IPAddyFrameView(root)
        self.model = IPAddyFrameModel()

        # configure view callbacks
        self.view.getbatches_btn_cb = self.get_batches

        if autogrid:
            self.view.grid(0, 0)

    def get_batches(self):
        _debug("callback called")
        ipv4 = self.view.get_ipv4()
        self.view.clear_batches()
        self.view.insert("Retrieving batches...")

        def common_cleanup():
            self.task = None
            self.view.enable_button()
        
        def timeout():
            self.view.clear_batches()
            self.view.insert("<Timeout Occurred>")
            common_cleanup()

        def complete(batches):
            self.view.clear_batches()
            self.view.insert_batches(b.name for b in batches.ids_to_batches.values())
            common_cleanup()

        def func():
            return self.model.get_batches(ipv4)

        self.view.disable_button()
        self.task = AsyncTask(self.root, func, complete, timeout)

    def grid(self, row, col):
        self.view.grid(row, col)

    def grid_forget(self):
        self.view.grid_forget()


class FilenameFrameView():
    def __init__(self, root):
        self.frame = mytk.SimpleFrame(root)
        self.listbox = mytk.SimpleListbox(self.frame, "Batch List:")
        self.browse = mytk.StatefulItemButton(self.frame, "Browse", self.browse_btn_cb)

    def browse_btn_cb(self):
        _debug("Unregistered %s callback called" % self.__class__.__name__)  # hook

    def grid(self, row, col):
        self.frame.grid(row=row, column=col)
        self.listbox.grid(0, 0)
        self.browse.grid(2, 0, sticky=tk.E)

    def grid_forget(self):
        self.frame.grid_forget()
        self.listbox.grid_forget()
        self.browse.grid_forget()


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


class AsyncTask():
    __fail = object()
    def __init__(self, root, func, on_completion=None, on_timeout=None, start=True, timeout=5):
        """ Asynchronous task. 
        :param root: tk.Tk()
        :param func: function to run. No arguments. May return value (see below)
        :param on_completion: callback on success. Passed result of `func()`. 
        :param on_timeout: callback if timeout occurs. No arguments. 
        :param start: automatically start. 
        :param timeout: timeout in seconds. 
        """
        self.root = root
        self.func = func
        self.on_completion_cb = on_completion
        self.on_timeout_cb = on_timeout
        self.success = False
        self.thread = threading.Thread(None, self.run, daemon=True)
        self.timeout = timeout
        self.on_fail_id = None
        self.check_id = None
        self.timed_out = False
        self.result = self.__fail
        if start:        
            self.start()

    def run(self):
        try:
            self.result = self.func()
        except Exception:
            if self.timed_out:
                pass  # timeout event already handled
            else:
                raise

    def on_timeout(self):
        self.timed_out = True
        if self.check_id:
            self.root.after_cancel(self.check_id)
        if self.on_timeout_cb:
            try:
                self.on_timeout_cb()
            except Exception as e:
                _debug("Exception occurred in timeout callback: %s" % e)

    def on_completion(self):
        if self.result is self.__fail:
            _debug("function failed")
        else:
            self.on_completion_cb(self.result)

    def start(self):
        self.on_fail_id = self.root.after(self.timeout*1000, self.on_timeout)
        self.thread.start()
        self.periodic_check()

    def periodic_check(self):
        def check():
            _debug("periodic check")
            if not self.thread.is_alive():
                self.success = True
                self.root.after_cancel(self.check_id)
                self.root.after_cancel(self.on_fail_id)
                if self.on_completion_cb:
                    self.on_completion_cb(self.result)
            else:
                self.check_id = self.root.after(100, check)
        self.check_id = self.root.after(100, check)    


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

        self.menubutton = mytk.SimpleMenu(self.root, self.on_menu_change,
                                     self.str_by_ip, [self.str_by_ip, self.str_by_fn])
        self.activate_frame(ip_frame)
        self.menubutton.grid(0, 0, sticky=tk.W)

    def mainloop(self):
        _debug("Beginning mainloop")
        self.root.mainloop()

    def activate_frame(self, frame):
        if self.active_frame:
            self.active_frame.grid_forget()
        self.active_frame = frame
        self.root.grid()
        self.active_frame.grid(1, 0)

    def on_menu_change(self, txt):
        if self.name_to_frames[txt] != self.active_frame:
            self.activate_frame(self.name_to_frames[txt])


if __name__ == '__main__':
    m = MixingTimeInterface()
    m.active_frame.view.gb_frame.entry_tv.set("192.168.1.7")
    m.mainloop()
