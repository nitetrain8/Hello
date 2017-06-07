import tkinter as tk
import tkinter.ttk as ttk

class EventDispatcher():
    def __init__(self):
        self.handlers = {}
        
    def create_event(self, ev):
        self.handlers[ev] = self.handlers.get(ev, [])
        
    def register(self, ev, handler):
        if ev not in self.handlers:
            self.create_event(ev)
        self.handlers[ev].append(handler)
        
    def unregister(self, ev, handler):
        self.handlers[ev].remove(handler)
        
    def fire(self, ev, *args):
        for h in self.handlers.get(ev, ()):
            h(ev, *args)
            
    def unregister_all(self, ev):
        self.handlers[ev] = []
        
    def create_callback(self, ev, *args):
        def cb():
            self.fire(ev, *args)
        return cb
            

class TkQuitHack(tk.Tk):
    def _hacky_monitor_running(self):
        # hack to allow closing tkinter window by 
        # "X" button in this interactive prompt
        # unsure if this is an ipython/mpl artifact or not
        # but it works
        def monitor():
            if not self._hacky_running:
                for cb in self._hacky_on_destroyed:
                    cb()
                self.quit()
                self.destroy()
                self._hacky_destroyed = True
                
            else:
                self.after(self._hacky_monitor_interval, monitor)
        self.after(self._hacky_monitor_interval, monitor)
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._hacky_running = True
        self._hacky_monitor_interval = 200
        self._hacky_monitor_running()
        self.protocol("WM_DELETE_WINDOW", self.hacky_destroy)
        self._hacky_destroyed = False
        self._hacky_on_destroyed = []
        
    def hacky_destroy(self):
        self._hacky_running = False
        
    def register_destroy_callback(self, cb):
        self._hacky_on_destroyed.append(cb)
        
    def is_destroyed(self):
        return self._hacky_destroyed


class LabeledEntry(tk.Frame):
    def __init__(self, master, text, def_value, events, value_changed_event, pos="top", *args, **kw):
        super().__init__(master, *args, **kw)
        self.label = tk.Label(self, text=text)
        self.entry = tk.Entry(self)
        
        if pos.lower() == "top":
            r1, c1 = 0, 0
            r2, c2 = 1, 0
        elif pos.lower() == "left":
            r1, c1 = 0, 0
            r2, c2 = 0, 1
        elif pos.lower() == "right":
            r1, c1 = 0, 1
            r2, c2 = 0, 0
        else:
            raise ValueError("Bad Position: %r" % pos)
            
        self.label.grid(row=r1, column=c1, sticky=(tk.E, tk.W))
        self.entry.grid(row=r2, column=c2, sticky=(tk.E, tk.W))
            
        if def_value is None:
            def_value = ""
        self.value = def_value
        self.set(def_value)
        self._trigger_mode = "on_change"
            
        self.entry.bind("<Return>", self.maybe_value_changed)
        self.entry.bind("<FocusOut>", self.maybe_value_changed)
        self.events = events
        self.value_changed_event = value_changed_event
        
    def label_width(self, value):
        self.label.config(width=value)
        
    def entry_width(self, value):
        self.entry.config(width=value)
        
    def maybe_value_changed(self, e):
        value = self.get()
        try:
            v = float(value or 0)
        except ValueError:
            print("Could not coerce string to float: %r" % value)
            return
        
        if v == float(self.value) and self._trigger_mode == "on_change" and \
                e.keycode != 13:
            return
        
        self.value = value
        self.trigger_value_changed(v)
        
    def trigger_value_changed(self, v):
            self.events.fire(self.value_changed_event, v)
        
    def get(self):
        return self.entry.get()
    
    def set(self, value):
        value = str(value)
        if not value:
            value = "0"
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)
        self.value = value
        
    def set_trigger_mode(self, mode):
        if mode not in ("always", "on_change"):
            raise ValueError("Unrecognized mode: %r" % mode)
        self._trigger_mode = mode
        
        
class EntryButton(tk.Frame):
    def __init__(self, master, text, events, event):
        super().__init__(master)
        self.entry = tk.Entry(self)
        self.entry.insert(0, 3600)
        self.button = ttk.Button(self, text=text, command=self.fire)
        self.entry.bind("<Return>", self.fire)
        self.events = events
        self.event = event
        
        self.entry.grid(row=0, column=1)
        self.button.grid(row=1, column=1)
        
    def fire(self, e=None):
        self.events.fire(self.event, self.entry.get())
    

# Patched tkinter settit. For some reason, setting the internal
# Variable isn't properly being used to update the OptionMenu
# widget text. 
      
# Also, this makes more sense as a function constructor
# than a class (imo)
    
def _setit(menu, var, value, cb=None):
    def func(*args):
        var.set(value)
        menu.config(text=value)
        if cb is not None:
            cb(value, *args)
    return func
        
# Patched tkinter optionmenu to work properly. The only changes
# are changing the default "textvariable" to "text" in kw to super,
# and re-running the code to bind to the patched _settit class. 

class PatchedOptionMenu(tk.Menubutton):
    """OptionMenu which allows the user to select a value from a menu."""
    def __init__(self, master, variable, value, *values, **kwargs):
        """Construct an optionmenu widget with the parent MASTER, with
        the resource textvariable set to VARIABLE, the initially selected
        value VALUE, the other menu values VALUES and an additional
        keyword argument command."""
        kw = {"borderwidth": 2, "text": value,
              "indicatoron": 1, "relief": tk.RAISED, "anchor": "c",
              "highlightthickness": 2}
        tk.Widget.__init__(self, master, "menubutton", kw)
        self.widgetName = 'tk_optionMenu'
        menu = self.__menu = tk.Menu(self, name="menu", tearoff=0)
        self.menuname = menu._w
        # 'command' is the only supported keyword
        callback = kwargs.get('command')
        if 'command' in kwargs:
            del kwargs['command']
        if kwargs:
            raise TclError('unknown option -'+kwargs.keys()[0])
        menu.add_command(label=value,
                 command=_setit(self, variable, value, callback))
        for v in values:
            menu.add_command(label=v,
                     command=_setit(self, variable, v, callback))
        self["menu"] = menu

    def __getitem__(self, name):
        if name == 'menu':
            return self.__menu
        return tk.Widget.__getitem__(self, name)

    def destroy(self):
        """Destroy this widget and the associated menu."""
        tk.Menubutton.destroy(self)
        self.__menu = None
        
        
class MenuFrame(tk.LabelFrame):
    def __init__(self, master, text, events, event, entries):
        super().__init__(master, text=text)
        self.entries = entries
        self.events = events
        self.event = event
        
        self.entries = []
        entry_names = []
        
        for i, (var, val, ev) in enumerate(entries, 1):
            w = LabeledEntry(self, var, val, events, ev)
            w.grid(row=i, column=0)
            self.entries.append(w)
            entry_names.append(var)
        
        self.tkvar = tk.StringVar(self)
        self.tkvar.set(entry_names[0])
        self.menu = OptionMenu(self, self.tkvar, *entry_names)
        self.menu.grid(column=0, row=0)
        self.events.register(self.event, self.on_menu_changed)
            
    def on_menu_changed(self, _):
        self.events.fire(self.event, self.tkvar.get())
        
            
class LabelFrameWithLabelEntries(tk.LabelFrame):
    def __init__(self, master, text, events, entries=()):
        super().__init__(master, text=text)
        self.events = events
        self.entries = []
        for text, val, ev in entries:
            self.add_entry(text, val, ev)
            
    def set_trigger_mode(self, mode):
        for e in self.entries:
            e.set_trigger_mode(mode)
            
    def add_entry(self, text, val, ev):
        e = LabeledEntry(self, text, val, self.events, ev, pos="left")
        e.label_width(10)
        e.entry_width(8)
        e.grid(row=len(self.entries), column=0)
        self.entries.append(e)
            
class LabelDisplay(tk.Frame):
    def __init__(self, master, events, event, text, value="", w1=None, w2=None):
        super().__init__(master)
        self.label = tk.Label(self, text=text, anchor=tk.E)
        self.display = tk.Label(self, text=value, anchor=tk.E)
        if w1:
            self.label.config(width=w1)
        if w2:
            self.display.config(width=w2)
        
        self.label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.display.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.events = events
        self.events.register(event, self.on_value_update)
        
    def on_value_update(self, ev, value, *args):
        self.set(value)
        
    def set(self, value):
        value = str(value)
        self.display['text'] = value
    
    def get(self):
        return self.display['text']
        
class LabelDisplayFrame(tk.LabelFrame):
    def __init__(self, master, text, events):
        super().__init__(master, text=text)
        self.labels = {}
        self.events = events
        
    def add_label(self, id, event, text, value="", w1=None, w2=None):
        label = LabelDisplay(self, self.events, event, text, value, w1, w2)
        label.grid(row=len(self.labels), column=0, sticky=(tk.E, tk.W, tk.N, tk.S))
        self.labels[id] = label
        
    def add_labels(self, *args):
        for a in args:
            self.add_label(*args)
        
class Combobox(ttk.Combobox):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        vcmd = self.register(self.nomodify,)
        self.config(validate="key", validatecommand=vcmd)
        self.bind("<Return>", lambda _: self.event_generate("<1>"))
        self.bind("<Button-1>", lambda _: self.event_generate("<Down>", when='head'))
        self.current(0)
        
    def nomodify(self):
        return False
        
class MenuLabel(tk.Frame):
    def __init__(self, master, text, events, event, values, w1=10, w2=6, map=None, **kw):
        super().__init__(master, **kw)
        self.label = tk.Label(self, text=text)
        self.label.config(width=w1)
        
        if map is None:
            map = {k:k for k in values}
        else:
            if not all(k in map for k in values):
                raise ValueError("Unmapped keys: " % " ".join(set(values)-set(map)))
        
        self.map = map
        self.events = events
        self.event = event
        
        self.menu = Combobox(self, values=values)
        self.menu.bind("<<ComboboxSelected>>", self.menu_selected)
        self.menu.config(width=w2)
        
        self.label.grid(row=0, column=0, sticky=(tk.E, tk.W, tk.N, tk.S))
        self.menu.grid(row=0, column=1, sticky=(tk.E, tk.W, tk.N, tk.S))
        
        
    def get_raw(self):
        return self.menu.get()
    
    def get(self):
        return self.map[self.menu.get()]
        
    def menu_selected(self, e):
        self.events.fire(self.event, self.get())
        
    