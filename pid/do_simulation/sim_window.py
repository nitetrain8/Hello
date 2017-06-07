from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
import tkinter as tk
import tkinter.ttk as ttk
from hello.pid.do_simulation.options import SimConfig
from hello.pid.ui import EventDispatcher, TkQuitHack, MenuFrame, MenuLabel, Combobox, \
                        EntryButton, LabelDisplay, LabelDisplayFrame, LabeledEntry, \
                        LabelFrameWithLabelEntries
from hello.pid.plots import Data, PVPlot, GasesPlot, PIDPlot, SeriesData
from hello.pid.do_simulation.do_sim import do_sim_coroutine
from hello.pid.lvpid import PIDController
from hello.pid.delay import m2s, s2m

class DOSimWindow():
    """ Sim Window handles common MPL functions & data storage 
    as well as non-MPL tkinter configuration 
    """
    def __init__(self, frame, sim_config, events):
        
        # Unpack config items
        self.cfg = sim_config
        self.update_interval = self.cfg.update_interval
        self.xwindow = self.cfg.xwindow_hrs
        
        # MPL objects
        self.fig = Figure(figsize=(self.cfg.fig_width, self.cfg.fig_height))
        ax1 = self.fig.add_subplot(411)
        ax2 = self.fig.add_subplot(412)
        ax3 = self.fig.add_subplot(413)
        ax4 = self.fig.add_subplot(414)
        for a in (ax1, ax2, ax3, ax4):
            b = a.get_position()
            a.set_position([b.x0, b.y0, b.width*0.9, b.height])
        
        self.xdata = Data(self.xwindow*3600)
        self.pv_plot = PVPlot(ax1, self.xdata, self.xwindow*3600)
        class SeriesData100(SeriesData):
            def put(self, v):
                self._pending.append(v*(100/0.21))
        self.pv_plot.add_series(("hs", dict(color="red", ls="-", label="HS")), klass=SeriesData100)

        self.gases_plot = GasesPlot(ax2, self.xdata, self.xwindow*3600)
        self.n2_pid_plot = PIDPlot(ax3, self.xdata, self.xwindow*3600)
        self.o2_pid_plot = PIDPlot(ax4, self.xdata, self.xwindow*3600)
        
        x_spacing = self.cfg.time_unit / (self.cfg.x_tick_interval * 3600)
        self.pv_plot.set_tick_interval(x_spacing)
        self.gases_plot.set_tick_interval(x_spacing)
        self.n2_pid_plot.set_tick_interval(x_spacing)
        self.o2_pid_plot.set_tick_interval(x_spacing)

        # misc
        self.pv_plot.axhline(self.cfg.simops.set_point)
        
        # Tkinter setup
        self.root = frame
        
        self.fig_frame = tk.Frame(self.root)
        
        # a tk.DrawingArea
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.fig_frame)
        self.canvas.show()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.root)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        self._running = False
        self._monitor_id = None
        self._monitor_interval = 500
        
        # coroutine support
        self.do_coro = None
        self._current_state = {}
        
        # Periodic update support
        self.updating = True
        
        # Event handling for callbacks
        # All event handling works by modifying
        # Commands are sent directly to the coroutine
        # via use of command codes. 
        # The primary code is (obviously) used to run
        # the simulation. All the codes used below 
        # signal the coroutine to take specific action,
        # including modifying stateful values
        
        self.events = events
        
        def register_update_state(event, arg):
            def on_modified(ev, value, *args):
                self.trigger_update_state(arg, value)
                print("State Value Updated: %s %s " % (arg, value))
            self.events.register(event, on_modified)
                
        register_update_state("SP_CHANGED", "sp")
        register_update_state("PV_CHANGED", "pv")
        register_update_state("MG_CHANGED", "mg")
        
        def set_target_line(event, value):
            self.pv_plot.axhline(value)
        self.events.register("SP_CHANGED", set_target_line)

        
        def on_pid_changed(ev, value, *args):
            ev = ev.lower()
            ctrl, param, _ = ev.split("_")
            ctrl += "_pid"
            print("Value Changed: %s.%s: %.2f" % (ctrl, param, value))
            self.trigger_update_value(ctrl, param, value)
            
        for c in "N2", "O2":
            for p in "PGAIN", "ITIME", "DTIME", "BETA", "MODE", "MAN":
                ev = "%s_%s_CHANGED" % (c,p)
                self.events.register(ev, on_pid_changed)
        
        def on_process_gain_changed(ev, value, *args):
            c = ev.split("_")[0].lower()
            if c == "kmult":
                c = "k_mult"
            self.trigger_update_value("process", c, value)
            print("Changed value: %s to %s" % (c, value))
            
        for c in "K", "KMULT", "C", "DC", "D2C", "DELAY":
            ev = c + "_CHANGED"
            self.events.register(ev, on_process_gain_changed)
            
        def on_timefactor_changed(ev, value, *args):
            self.cfg.time_factor = value
            print(ev, ":", value)
        self.events.register("TIMEFACTOR_CHANGED", on_timefactor_changed)
        
        def on_clear_all_data(ev, *args):
            self.xdata.clear()
            for p in self.iter_plots():
                p.clear()
            self.do_coro.send(("SET_TIME", 0))
        self.events.register("CLEAR_ALL_DATA", on_clear_all_data)
        
        def on_advance_sim(ev, value, *args):
            if not value: return
            try:
                value = int(value)
            except ValueError:
                print("Invalid value: %r" % value)
                return
            print("Advancing simulation %d seconds..." % value)
            self._run_sim(value)
        self.events.register("ADVANCE_SIM", on_advance_sim)
        
        def on_legend_clicked(event):
            ll = event.artist
            series = self.leg_map[ll]
            series.toggle_visible()
            
        def on_xwindow_changed(ev, value, *args):
            nv = int(value * 3600)
            for p in self.iter_plots():
                for s in p.series:
                    if len(s) != nv:
                        s.resize(nv)
            if len(self.xdata) != nv:
                self.xdata.resize(nv)
        self.events.register("XWINDOW_CHANGED", on_xwindow_changed)
            
        # legend picker support
        self.leg_map = {}
        for p in self.iter_plots():
            m = p.get_leg_map()
            for leg, s in m.items():
                leg.set_picker(5)
                self.leg_map[leg] = s
        self.fig.canvas.mpl_connect("pick_event", on_legend_clicked)

        
    def trigger_update_value(self, ob, name, value):
        cmd = "UPDATE_VALUE"
        args = (ob, name, value)
        self.do_coro.send((cmd, args))
        
    def trigger_update_state(self, name, value):
        cmd = "MODIFY_STATE"
        args = (name, value)
        self.do_coro.send((cmd, args))
        
    def iter_plots(self):
        return (self.pv_plot, self.gases_plot, self.n2_pid_plot, self.o2_pid_plot)
        
    def pack(self, side=tk.TOP, fill=tk.BOTH, expand=1):
        self.fig_frame.pack(side=side, fill=fill, expand=expand)
        
    def start(self):
        self._updating = True
        self.begin_sim()
        self.schedule_update()
        
    def stop(self):
        self._updating = False
        
    def resume(self):
        if not self.do_coro:
            self.start()
        else:
            self.schedule_update()
        
    def begin_sim(self):
        self.do_coro = do_sim_coroutine(self.cfg.simops, self._current_state,
                         self.xdata, self.pv_plot.pv, self.pv_plot.c, self.gases_plot.co2,
                         self.gases_plot.n2, self.gases_plot.o2, self.gases_plot.air,
                         self.n2_pid_plot.uk, self.n2_pid_plot.up, self.n2_pid_plot.ui, self.n2_pid_plot.ud,
                         self.o2_pid_plot.uk, self.o2_pid_plot.up, self.o2_pid_plot.ui, self.o2_pid_plot.ud,
                         self.pv_plot.hs)
        next(self.do_coro)
        
    def update(self):
        n = self.cfg.time_factor
        n = int(n)
        self._run_sim(n)
        self.events.fire("PROCESS_STATE_UPDATE", self._current_state.copy())
        
    def _run_sim(self, n):
        self.do_coro.send(("SIM_ITERS", n))
        
        self.xdata.push(n)
        self.pv_plot.push(n)
        self.gases_plot.push(n)
        self.o2_pid_plot.push(n)
        self.n2_pid_plot.push(n)
        
        self.pv_plot.update()
        self.gases_plot.update()
        self.n2_pid_plot.update()
        self.o2_pid_plot.update()
        
        self.fig.canvas.draw()
        
    def schedule_update(self):
        def update(self=self):
            if self.updating:
                self.update()
                self.root.after(self.update_interval, update)
        self.root.after(self.update_interval, update)    
    

from hello.pid.ui import *

class StatusDisplay(LabelDisplayFrame):
    def __init__(self, master, text, events, cfg):
        super().__init__(master, text, events)

        # text config....
        c,n,o = cfg.simops.initial_request_cno
        a = 1-(c+n+o)
        sub2 = "\u2082:"
        co2 = "CO"+sub2
        n2 = "N"+sub2
        o2 = "O"+sub2
        
        self.add_label("PV", "PV_PROCESS_UPDATE", "PV:", cfg.simops.initial_pv, 3, 6)
        self.add_label("CO2", "CO2_PROCESS_UPDATE", co2, "%.1f%%" % (c*100), 3, 6)
        self.add_label("N2", "N2_PROCESS_UPDATE", n2, "%.1f%%" % (n*100), 3, 6)
        self.add_label("O2", "O2_PROCESS_UPDATE", o2, "%.1f%%" % (o*100), 3, 6)
        self.add_label("Air", "AIR_PROCESS_UPDATE", "Air:", "%.1f%%" % (a*100), 3, 6)
        
        self.add_label("c", "C_PROCESS_UPDATE", "c:", cfg.simops.c, 3, 6)
        self.add_label("dc", "DC_PROCESS_UPDATE", "dc:", cfg.simops.dc, 3, 6)
        self.add_label("d2c", "D2C_PROCESS_UPDATE", "d\u00B2c:", cfg.simops.d2c, 3, 6)
        
        self.events.register("PROCESS_STATE_UPDATE", self.on_state_update)
        
    def on_state_update(self, ev, state, *args):
        self.labels['c'].set("%.4g" % state['c'])
        self.labels['dc'].set("%.4g" % state['dc'])
        self.labels['d2c'].set("%.4g" % state['d2c'])
        
        self.labels['PV'].set("%.2f%%" % state['pv'])
        self.labels["CO2"].set("%.1f%%" % (state['co2_req']*100))
        self.labels["N2"].set("%.1f%%" % (state['n2_req']*100))
        self.labels["O2"].set("%.1f%%" % (state['o2_req']*100))
        self.labels["Air"].set("%.1f%%" % (state['air_req']*100))
        
class PIDFrame(LabelFrameWithLabelEntries):
    def __init__(self, master, text, events, prefix, pid_ops):
        super().__init__(master, text, events)
        
        self.add_entry("PGain:", pid_ops.p, prefix + "_PGAIN_CHANGED")
        self.add_entry("ITime:", pid_ops.i, prefix + "_ITIME_CHANGED")
        self.add_entry("DTime:", pid_ops.d, prefix + "_DTIME_CHANGED")
        self.add_entry("Beta:", pid_ops.beta, prefix + "_BETA_CHANGED")
        self.add_entry("Man:", pid_ops.man_request, prefix + "_MAN_CHANGED")
        
        # Modes
        modes = [
            ("Auto", PIDController.AUTO),
            ("Man", PIDController.MAN),
            ("Off", PIDController.OFF)
        ]
        mode_order = [m[0] for m in modes]
        map = dict(modes)
        self.menu = MenuLabel(self, "Mode:", events, prefix + "_MODE_CHANGED", mode_order, map=map)
        self.menu.grid(row=len(self.entries), column=0, sticky=(tk.E,tk.W,tk.N,tk.S))
        

class PIDSimFrame():
    def __init__(self, master, sim_cfg, events=None):
        if events is None:
            events = EventDispatcher()
        self.cfg = sim_cfg
        ops = self.cfg.simops
        self.events = events
        self.frame = tk.Frame(master)
        self.w = DOSimWindow(self.frame, sim_cfg, events)
        self.w.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        self.settings_frame = sf = tk.Frame(self.frame)
        self.settings_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
        
        # Widgets
        
        # N2 PID
        n2pid = PIDFrame(sf, "N\u2082 PID:", events, "N2", ops.n2_pid)

        # O2 PID
        o2pid = PIDFrame(sf, "O\u2082 PID:", events, "O2", ops.o2_pid)  
        
        # Process values
        proc = LabelFrameWithLabelEntries(sf, "Process:", events)
        proc.add_entry("Set Point:", ops.set_point, "SP_CHANGED")
        proc.add_entry("PV:", ops.initial_pv, "PV_CHANGED")
        proc.add_entry("k:", ops.k, "K_CHANGED")
        proc.add_entry("k_mult:", ops.k_mult, "KMULT_CHANGED")
        proc.add_entry("delay:", s2m(ops.delay), "DELAY_CHANGED")
        
        # Simulation options
        sim = LabelFrameWithLabelEntries(sf, "Simulation:", events)
        sim.add_entry("time factor:", self.cfg.time_factor, "TIMEFACTOR_CHANGED")
        sim.add_entry("x window(hr):", self.cfg.xwindow_hrs, "XWINDOW_CHANGED")
        
        # buttons
        clear = ttk.Button(sf, text="Clear", command=events.create_callback("CLEAR_ALL_DATA"))
        advance = EntryButton(sf, "Advance(s)", events, "ADVANCE_SIM")

        # Consumption constants
        c_frame = LabelFrameWithLabelEntries(sf, "Consumption:", events)
        c_frame.add_entry("c", ops.c, "C_CHANGED")
        c_frame.add_entry("dc/dt", 0, "DC_CHANGED")
        c_frame.add_entry("d\u00B2c/dt\u00B2", 0, "D2C_CHANGED")
        c_frame.set_trigger_mode("always")
        
        # Output display
        cstate = StatusDisplay(sf, "Current:", events, self.cfg)    
        
        tk_all = (tk.E, tk.W, tk.N, tk.S)
        n2pid.grid(row=1, column=1, sticky=tk_all)
        o2pid.grid(row=1, column=2, sticky=tk_all)
        
        proc.grid(row=2, column=1, sticky=tk_all)
        sim.grid(row=2, column=2, sticky=tk_all)

        c_frame.grid(row=3, column=1, rowspan=3, sticky=(tk.E, tk.W, tk.N, tk.S))
        cstate.grid(row=3, column=2, rowspan=8, sticky=(tk.E, tk.W, tk.N, tk.S))
        
        advance.grid(row=11, column=1)
        clear.grid(row=11, column=2, sticky=tk.S)
        
        self.wl = {}
        self.wl.update((k,v) for k,v in locals().items() if isinstance(v, tk.Widget))
        
        self.w.start()
        master.register_destroy_callback(self.w.stop)
        
        self.n2pid = n2pid
        self.o2pid = o2pid
        
        
    def pack(self, **kw):
        self.frame.pack(**kw)
        
        