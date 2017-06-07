from matplotlib.ticker import MultipleLocator, FuncFormatter
import numpy as np

class RingBuffer():
    """ Numpy-based ring buffer """

    def __init__(self, maxsize, dtype=np.float32):
        if not maxsize or maxsize < 0:
            raise ValueError("%s requires max size argument" % self.__class__.__name__)
        self._queue = np.zeros(maxsize, dtype)
        self._dtype = dtype
        self._maxsize = maxsize
        self._end = 0
        self._sz = 0

    def put(self, d):
        self._queue[self._end] = d
        self._end += 1
        if self._end >= self._maxsize:
            self._end = 0
        if self._sz < self._maxsize:
            self._sz += 1

    def put_list(self, lst):
        """
        :param lst: list to extend data from
        :type lst: list | tuple | np.ndarray
        """
        slen = len(lst)
        if slen > self._maxsize:
            self._queue = np.array(lst, dtype=self._dtype)[-self._maxsize:]
            self._sz = self._maxsize
            self._end = 0
            return
        if slen + self._end <= self._maxsize:
            start = self._end
            end = slen + self._end
            self._queue[start:end] = lst
            self._end = end
        else:
            # add slice in two steps
            first_step = self._maxsize - self._end
            self._queue[self._end: self._maxsize] = lst[:first_step]
            second_step = slen - first_step
            self._queue[:second_step] = lst[first_step:]
            self._end = second_step

        if self._sz < self._maxsize:
            self._sz += slen
        if self._end == self._maxsize:
            self._end = 0

    def extend(self, it):
        try:
            it.__len__  # list, tuple, nparray
        except AttributeError:
            it = tuple(it)
        self.put_list(it)

    def get(self):
        """
        Get method. Returns the entire queue but does NOT
        drain the queue.
        """
        if self._sz < self._maxsize:
            return self._queue[: self._end]
        else:
            return np.roll(self._queue, -self._end)

    def __len__(self):
        return self._sz

    def clear(self):
        self._end = 0
        self._sz = 0


class Data():
    """ Standard data container for a single set of data
    Stores permenant data internally in a RingBuffer.
    For performance reasons, store pending values 
    in a simple python list, and push them to the 
    permanent buffer only when explicitly requested. 
    """
    def __init__(self, pts):
        self._values = RingBuffer(pts)
        self._pending = []
    
    def __len__(self):
        return len(self._values)
        
    def push(self, n=None):
        if n is not None:
            self._values.extend(self._pending[:n])
            self._pending = self._pending[n:]
        else:
            self._values.extend(self._pending)
            self._pending.clear()

    def put(self, v):
        self._pending.append(v)
        
    def get(self):
        self.push(None)
        return self._values.get()

    def clear(self):
        self._values.clear()
        self._pending.clear()
        
    def resize(self, new_sz):
        nv = RingBuffer(new_sz)
        nv.extend(self.get())
        self._values = nv


class SeriesData(Data):
    def __init__(self, name, ax, xdata, pts, **line_kw):
        self.name = name
        super().__init__(pts)
        self.x = xdata
        self.line, = ax.plot((), (), **line_kw)
        
    def update_line(self):
        self.line.set_data(self.x.get(), self.get())
        
    def hide(self):
        self.line.set_visible(False)
        
    def show(self):
        self.line.set_visible(False)
        
    def set_visible(self, visible):
        self.line.set_visible(visible)
        
    def get_visible(self):
        return self.line.get_visible()
    
    def toggle_visible(self):
        self.set_visible(not self.get_visible())
        
    
# Plot classes contain custom configuration code
# so SimWindow doesn't need to know how to set them up

class Plot():
    def __init__(self, ax, xdata, pts, yformatter=None, *series_ops):
        self.ax = ax
        self.x = xdata
        self.pts = pts
        self.series = []
        for ops in series_ops:
            self.add_series(ops, False)
        b = ax.get_position()
        #ax.set_position([b.x0+0.05, b.y0, b.width*0.8, b.height])
        ax.legend(bbox_to_anchor=(0.99, 1.06), loc="upper left")
        self.update_legend()
        ax.grid()
        if yformatter:
            ax.yaxis.set_major_formatter(yformatter)
        self._hline = None
        self._hline_minus = None
        self._hline_plus = None

    def update_legend(self):
        self.ax.legend(bbox_to_anchor=(0.99, 1.06), loc="upper left")
        self.leg_line_map = {}
        for lline, s in zip(self.ax.legend_.get_lines(), self.series):
            self.leg_line_map[lline] = s

    def add_series(self, ops, update_leg=True, klass=SeriesData):
        name, kw = ops
        kw['ls'] = kw.get('ls') or "-"
        s = klass(name, self.ax, self.x, self.pts, **kw)
        self.series.append(s)
        setattr(self, name, s)
        if update_leg:
            self.update_legend()
        
    def get_leg_map(self):
        return self.leg_line_map.copy()
            
    def put(self, *values):
        if len(values) != len(self.series):
            raise ValueError("Invalid argument to put: got %d values (expected %d)" \
                            % (len(values), len(self.series)))
        for s, v in zip(self.series, values):
            s.put(v)
            
    def push(self, n):
        for s in self.series:
            s.push(n)
            
    def update(self):
        for s in self.series:
            s.update_line()
        self.rescale()
        
    def rescale(self):
        self.ax.relim(True)
        self.ax.autoscale_view(True,True,True)
        
    def axhline(self, y, db=None, **kw):
        kw['ls'] = kw.get('ls') or "--"
        kw['color'] = kw.get('color') or 'black'
        kw['linewidth'] = kw.get('linewidth') or 1
        
        for h in (self._hline, self._hline_plus, self._hline_minus):
            if h:
                h.remove()

        if db is not None and db > 0:
            kw2 = kw.copy()
            kw2['linewidth'] = kw['linewidth'] / 2
            self._hline_plus = self.ax.axhline(y=y+db, **kw2)
            self._hline_minus = self.ax.axhline(y=y-db, **kw2)
        self._hline = self.ax.axhline(y=y, **kw)
        
    def set_tick_interval(self, n):
        l = MultipleLocator(n)
        self.ax.xaxis.set_major_locator(l)
        
    def clear(self):
        for s in self.series:
            s.clear()
            
class DummyPlot():
    def __init__(self, *series):
        class DummySeries():
            def update_line(self, *args):
                pass
            def clear(self, *args):
                pass
            def put(self, *args):
                pass
        class DummyAx():
            def relim(*args):
                pass
            def autoscale_view(*args):
                pass
        self.ax = DummyAx()
        for s in series:
            setattr(self, s, DummySeries())
    def clear(*args, **kw): pass
    def set_tick_interval(*args, **kw): pass
    def axhline(*args, **kw): pass
    def rescale(*args, **kw): pass
    def update(*args, **kw): pass
    def push(*args, **kw): pass
    def put(*args, **kw): pass
    def get_leg_map(*args, **kw): return {}


class PVPlot(Plot):
    """ Plot for PV """
    ypadding = 5
    def __init__(self, ax, xdata, pts, ylabel=None):
        series = [
            ("pv", dict(color="blue", ls="-", label="PV")),
            ("c", dict(color="green", ls="-", label="c"))
        ]
        fm = FuncFormatter(lambda y, _: "%.2f%%"%y)
        super().__init__(ax, xdata, pts, fm, *series)
        self.c.line.set_visible(False)
        if ylabel:
            self.ax.set_ylabel(ylabel)
        
    def rescale(self):
        self.ax.relim(True)
        self.ax.autoscale_view(True,True,True)
        lower, upper = self.ax.get_ybound()
        padding = self.ypadding
        self.ax.set_ylim(lower - padding, upper + padding, True, None)
    

class GasesPlot(Plot):
    def __init__(self, ax, xdata, pts, ylabel=None):
        
        series = [
            ("co2", dict(color="purple", ls="-", label="CO2")),
            ("n2", dict(color="red", ls="-", label="N2")),
            ("o2", dict(color="green", ls="-", label="O2")),
            ("air", dict(color="cyan", ls="-", label="Air")),
        ]
        fm = FuncFormatter(lambda y, _: "%d%%"%(y*100))
        super().__init__(ax, xdata, pts, fm, *series)
        self.ax.set_ylim((-0.05, 1.1))
        if ylabel:
            self.ax.set_ylabel(ylabel)
        
    def rescale(self):
        self.ax.relim(True)
        self.ax.autoscale_view(True,True,False)
        
        
class PIDPlot(Plot):
    def __init__(self, ax, xdata, pts):
        series = [
            ("uk", dict(color="blue", ls="-", label="Uk")),
            ("up", dict(color="red", ls="-", label="Up")),
            ("ui", dict(color="green", ls="-", label="Ui")),
            ("ud", dict(color="purple", ls="-", label="Ud")),
        ]
        
        super().__init__(ax, xdata, pts, None, *series)