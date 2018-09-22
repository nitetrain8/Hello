import clipboard
from hello.hello3 import open_hello, NotLoggedInError, HelloError
from pysrc.snippets import unique_name
from time import sleep, time
from datetime import datetime
import threading

_gmv_keys = [
    'temperature.output', 
    'temperature.man', 
    'temperature.interlocked', 
    'temperature.pv', 
    'temperature.sp', 
    'temperature.error', 
    'temperature.mode', 
    'agitation.output', 
    'agitation.man', 
    'agitation.interlocked', 
    'agitation.pv', 
    'agitation.sp', 
    'agitation.error', 
    'agitation.mode', 
    'ph.manUp',
    'ph.outputDown',
    'ph.error',
    'ph.pv',
    'ph.sp',
    'ph.manDown',
    'ph.outputUp',
    'ph.mode',
    'ph.interlocked',
    'do.manUp',
    'do.outputDown',
    'do.error',
    'do.pv',
    'do.sp',
    'do.manDown',
    'do.outputUp',
    'do.mode',
    'do.interlocked',
    'maingas.error',
    'maingas.man',
    'maingas.mode',
    'maingas.pv',
    'maingas.interlocked',
    'MFCs.air',
    'MFCs.n2',
    'MFCs.o2',
    'MFCs.co2',
    'condenser.output',
    'condenser.man',
    'condenser.pv',
    'condenser.sp', 
    'condenser.error', 
    'condenser.mode',
    'pressure.error',
    'pressure.pv',
    'level.error',
    'level.pv'
]

def print_keys(copy=True, silent=True):
    s = "keys = " + "[" + "\n    " + ",\n    ".join(repr(k) for k in _gmv_keys) + "\n]"
    if copy:
        clipboard.copy(s)
    if not silent:
        print(s)
    return s


def now(t):
    return datetime.fromtimestamp(t).strftime("%m/%d/%y %I:%M:%S %p")

def sleep10(s):
    st = time()
    end = st + s
    while end - time() > 10:
        sleep(10)
    if end - time() > 0:
        sleep(end - time())
        
        
def _join(*args):
    return "\n".join(args)
        
        
class _HLProtocol():
    def __init__(self, ip, wl):
        self._h = open_hello(ip)
        self._whitelist = None
        self._buf = []
        self._used_keys = ()
        self._st = time()
        self._mk_keys(wl)
        
    def reset_time(self):
        self._st = time()
    
    def _mk_keys(self, wl):
        """ Preserve key order, honor arbirary iterators """
        keys = []
        seen = set()
        for k in wl:
            if k in seen:
                continue
            seen.add(k)
            try:
                k1, k2 = k.split(".")
            except ValueError:  # no ".", bad key
                raise ValueError("%r is an invalid key" % k) from None
            keys.append((k1, k2))
        self._used_keys = tuple(keys)
        self._whitelist = seen
        self._write_key_update()

    def _list_wl_from_wl(self):
        return list(map(".".join, self._used_keys))
    
    def _write_key_update(self):
        s = "Time,Elapsed," + ",".join(".".join(k) for k in self._used_keys)
        self._write(s)
        self.log_data()
        
    def write_headers(self):
        self._write_key_update()
        
    def _write(self, s):
        if not s:
            return
        self._buf.append(s)
        
    def write_all(self, f):
        if not self._buf:
            return
        self._buf.append("")  # for newline at end of string
        try:
            f.write("\n".join(self._buf))
            f.flush()
        except OSError as e:
            print("Error Logging Data! %s"%e)
        else:
            self._buf.clear()
        
    def _call(self, f, *args, **kw):
        while True:
            try:
                return f(*args, **kw)
            except NotLoggedInError:
                self._h.login()
                
    def add_vars(self, *va):
        wl = self._list_wl_from_wl()
        wl.extend(va)
        self._mk_keys(wl)
        
    def stop_logging(self, *va):
        wl = self._list_wl_from_wl()
        sva = set(va)
        wl = [v for v in wl if v not in sva]
        self._mk_keys(wl)
                
    def _gmv(self):
        return self._call(self._h.gpmv)
        
    def _query(self):
        mv = self._gmv()
        t = time()
        d = [now(t), t-self._st]
        for k1, k2 in self._used_keys:
            v = mv[k1][k2]
            d.append(v)
            # ov = self._last[k]
            # if ov != v:
            #     self._last[k] = v
            #     d.append(v)
            # else:
            #     d.append("")
        return d
    
    def log_data(self):
        d = self._query()
        _s = str
        s = ",".join(_s(v) for v in d)
        self._write(s)
        

class EmptyFile():
    def write(self, s):
        pass
    def flush(self):
        pass
    def close(self):
        pass


class HelloLogger():
    def __init__(self, ip, interval=10, fn="hellolog.hl", whitelist=_gmv_keys.copy(), write_interval=300, verbose=False):
        self.verbose = verbose
        if fn is not None:
            fn = unique_name(fn)
        self.fn = fn
        self._f = None
        self.interval = interval
        
        self._wl = whitelist
        self._ip = ip
        self._proto = _HLProtocol(ip, whitelist)
        self._write_interval = write_interval
        self._next_write = 0
        self._file_lock = threading.RLock()
        
    def print(self, *args, **kw):
        if self.verbose:
            print(*args, **kw)
            
    def new_file(self, fn, reset_time=True):
        with self._file_lock:
            self.write_to_file()
            self._f.close()
            if fn is not None:
                self.fn = unique_name(fn)
                self._f = open(fn, 'w')
            else:
                self.fn = None
                self._f = EmptyFile()
            if reset_time:
                self._proto.reset_time()
            self._proto.write_headers()
            
    def write_to_file(self):
        with self._file_lock:
            self._proto.write_all(self._f)
    
    def start(self):
        if self.fn is None:
            self._f = EmptyFile()
        else:
            with self._file_lock:
                self._f = open(self.fn, 'w')
        self._stop = False
        self._thread = threading.Thread(None, self.run, daemon=True)
        self._thread.start()
        self.print("Logging Started")
        
    def add_logging_vars(self, *va):
        self._proto.add_vars(*va)
        
    def stop_logging_vars(self, *va):
        self._proto.stop_logging(*va)
        
    def run(self):
        t1 = Task(self._proto.log_data, self.interval)
        t2 = Task(self.write_to_file, self._write_interval)
        rir1 = t1.run_if_ready
        rir2 = t2.run_if_ready
        sleep_ = sleep
        self._proto.reset_time()
        while not self._stop:
            with self._file_lock:
                rir1()
                rir2()
            sleep_(1)
        
    def stop(self):
        self._stop = True
        self._thread.join()
        self.finish()
        self.print("Stopped successfully")
    
    def finish(self):
        if self._f is not None:
            self.write_to_file()
            self._f.close()
            self._f = None

class Task():
    def __init__(self, fn, interval):
        self.fn = fn
        self.interval = interval
        self.next_run = 0
        
    def run(self):
        self.next_run = time() + self.interval
        try:
            self.fn()
        except Exception as e:
            print("Exception in HelloLogger worker thread: %s"%e)

    def run_if_ready(self):
        if time() > self.next_run:
            self.run()
