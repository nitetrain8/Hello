"""

Created by: Nathan Starkweather
Created on: 08/01/2014
Created in: PyCharm Community Edition


"""
import threading
from traceback import print_exc

__author__ = 'Nathan Starkweather'

from xml.etree.ElementTree import parse as xml_parse
from urllib.request import urlopen
from urllib.error import URLError
from queue import Queue, Empty
from io import BytesIO
from collections import OrderedDict


ipv4def = "192.168.1.7"


def call_hello(url):
    req = urlopen(url, timeout=1)
    txt = req.read()
    return txt


def xml_parse_call(txt):
    buf = BytesIO(txt)
    tree = xml_parse(buf)
    root = tree.getroot()
    return root


def sendroutine(f):
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        g = f(*args, **kwargs)
        next(g)
        return g.send
    return wrapper


def getMainValues(urlbase):
    url = urlbase + "call=getMainValues"
    txt = call_hello(url)
    return xml_parse_call(txt)


def getAdvancedValues(urlbase):
    url = urlbase + "call=getAdvancedValues"
    txt = call_hello(url)
    return xml_parse_call(txt)


# noinspection PyAttributeOutsideInit
class Hello():
    def __init__(self, ipv4=ipv4def):
        self.url_base = "http://{ipv4}/webservice/interface/?&".format(ipv4=ipv4)
        self.mvhb = 0
        self.avhb = 0
        self.mvbad = 0
        self.avbad = 0
        self.main_values = OrderedDict(
            (("agitation", OrderedDict(
                    (
                        ("pv", 0),
                        ("sp", 0),
                        ("man", 0),
                        ("mode", 0),
                        ("interlocked", 0),
                        ("error", 0)
                    )
                ),
            ),
             ("temperature", OrderedDict(
                   (
                        ("pv", 0),
                        ("sp", 0),
                        ("man", 0),
                        ("mode", 0),
                        ("interlocked", 0),
                        ("error", 0)
                    )
                 ),
             ),
             
             ("secondaryheat", OrderedDict(
                    (
                        ("pv", 0),
                        ("sp", 0),
                        ("man", 0),
                        ("mode", 0),
                        ("interlocked", 0),
                        ("error", 0)
                    )
                ),
            ),

            ("maingas", OrderedDict(
                    (
                        ("pv", 0),
                        ("sp", 0),
                        ("man", 0),
                        ("mode", 0),
                        ("interlocked", 0),
                        ("error", 0)
                    )
                ),
            ),
            ("do", OrderedDict(
                    (("pv", 0),
                    ("sp", 0),
                    ("manUp", 0),
                    ("manDown", 0),
                    ("mode", 0),
                    ("error", 0))
                ),
            ),
            ("ph", OrderedDict(
                    (("pv", 0),
                    ("sp", 0),
                    ("manUp", 0),
                    ("manDown", 0),
                    ("mode", 0),
                    ("error", 0))
                ),
            ),
            ("pressure", OrderedDict(
                    (("pv", 0),
                    ("mode", 0),
                    ("error", 0))
                ),
            ),
            ("level", OrderedDict(
                    (("pv", 0),
                    ("mode", 0),
                    ("error", 0))
                ),
            ),
            ("condenser", OrderedDict(
                    (("pv", 0),
                    ("mode", 0),
                    ("error", 0))
                )
            ))
        )

        self.adv_values = OrderedDict(
            (("GasOut%", 0),
            ("N2 Flow (%)", 0),
            ("O2 Flow (%)", 0),
            ("CondenserDuty", 0),
            ("Lq Duty (%)", 0),
            ("CO2Duty(%)", 0),
            ("MainHeatDuty(%)", 0),
            ("MFCAirFlowFeedback(LPM)", 0),
            ("MFCN2FlowFeedback(LPM)", 0),
            ("MFCO2FlowFeedback(LPM)", 0),
            ("MFCCO2FlowFeedback(LPM)", 0),
            ("FilterOvenDutyUser(%)", 0),
            ("FilterOvenSP(C)", 0),
            ("GasOutLPM", 0),
            ("ManGasOut%M A", 0),
            ("ReqMainGasMode A", 0),
            ("SH Duty", 0),
            ("User SH Duty A", 0),
            ("SH Setpoint A", 0))
        )
        
        self.unack_count = 0

        self.mv_cont = mvc = {}
        self.av_cont = avc = {}

        # obsfucated deep copy
        for k1, v1 in self.main_values.items():
            mvc[k1] = mvcv1 = {}
            for k2, v2 in v1.items():
                mvcv1[k2] = v2

        for k, v in self.adv_values.items():
            avc[k] = v

        self.main_values.move_to_end("secondaryheat")
        self.adv_values.move_to_end("SH Duty", False)

        from hello import HelloApp
        self.app = HelloApp(ipv4)

    def getMainValues(self):
        return self.get_mainvalues()

    def getAdvancedValues(self):
        return self.get_advvalues()
        
    def getUnAckCount(self):
        try:
            rv = self.unackqueue.get(False)
        except Empty:
            rv = None
        else:
            self.unackqueue.task_done()
        return rv

    def setup(self):
        from tkinter import Tk, N, StringVar
        from tkinter.ttk import LabelFrame, Label

        root = Tk()
        mframe_label = StringVar(value="Loading...")
        mframe = LabelFrame(root, text="Loading...")
        group_frames = OrderedDict()
        labels = OrderedDict()
        views = OrderedDict()

        for cntlr, cntlr_vals in self.main_values.items():
            gframe = LabelFrame(mframe, text=cntlr)
            group_frames[cntlr] = gframe
            group_labels = OrderedDict()
            group_vars = OrderedDict()
            for k, v in cntlr_vals.items():
                name_var = StringVar(value=k)
                val_var = StringVar(value=v)
                name_label = Label(gframe, textvariable=name_var)
                val_label = Label(gframe, textvariable=val_var)
                group_labels[k] = [name_label, val_label]
                group_vars[k] = [name_var, val_var]
            labels[cntlr] = group_labels
            views[cntlr] = group_vars

        avframe = LabelFrame(mframe, text="Advanced Values")
        group_frames['Advanced Values'] = avframe
        avlabels = OrderedDict()
        labels['Adv'] = avlabels
        avvars = OrderedDict()
        views['Adv'] = avvars

        for k, v in self.adv_values.items():
            name_var = StringVar(value=k)
            val_var = StringVar(value=v)
            name_label = Label(avframe, textvariable=name_var)
            val_label = Label(avframe, textvariable=val_var)
            avlabels[k] = [name_label, val_label]
            avvars[k] = [name_var, val_var]

        for i, frame in enumerate(group_frames.values()):
            frame.grid(sticky=N, column=i, row=0)
        for cntlr in labels.values():
            for label in cntlr.values():
                label[0].grid()
                label[1].grid()
        mframe.grid()

        self.mframe = mframe
        self.root = root
        self.mframe_label = mframe_label
        self.gframes = group_frames
        self.labels = labels
        self.vars = views

        # Initialize threading model for polling updates
        # From server
        self.mvqueue = Queue(1)
        self.avqueue = Queue(1)
        self.unackqueue = Queue(1)

        self.mv_stop = threading.Event()
        self.av_stop = threading.Event()
        self.unack_stop = threading.Event()

        poll_lock = threading.Lock()

        self.mvthread = threading.Thread(None, self.do_mainvalues, None,
                                         (self.mvqueue, self.app, self.mv_stop, poll_lock))
        self.avthread = threading.Thread(None, self.do_advvalues, None,
                                         (self.avqueue, self.app, self.av_stop, poll_lock))
        self.unackthread = threading.Thread(None, self.do_unackcount, None, 
                                         (self.unackqueue, self.app, self.unack_stop, poll_lock))

        self.mvthread.daemon = True
        self.avthread.daemon = True
        self.unackthread.daemon = True

        self.mvthread.start()
        self.avthread.start()
        self.unackthread.start()

    def mainloop(self):
        self.setup()
        self.root.after(250, self.poll)
        try:
            self.root.mainloop()
        finally:
            # clean up threads
            
            # set stop flags
            self.mv_stop.set()
            self.av_stop.set()
            self.unack_stop.set()
            
            # empty queue to ensure threads aren't blocked
            for q in (self.mvqueue, self.avqueue, self.unackqueue):
                try:
                    q.get(False)
                except Empty:
                    pass
                else:
                    q.task_done()
            for t in (self.mvthread, self.avthread, self.unackthread):
                t.join()
            

    def poll(self):

        update = False
        try:
            root = self.getMainValues()
            if root:
                self.parse_main_values2(root)
                self.mvhb += 1
                update = True
            else:
                if root is not None:
                    raise Exception("unknown exception")
        except Exception:
            print("Error updating Main Values")
            print_exc()
            self.mvbad += 1

        try:
            root = self.getAdvancedValues()
            if root:
                self.parse_adv_values2(root)
                self.avhb += 1
                update = True
            else:
                if root is not None:
                    raise Exception("unknown exception")
        except Exception:
            print("Error updating Advanced Values")
            print_exc()
            self.avbad += 1
            
        try:
            unack_count = self.getUnAckCount()
            if unack_count is not None:
                self.unack_count = unack_count
        except Exception:
            print("Error getting unackcount")
            print_exc()

        self.root.after(250, self.update, update)
        self.root.after(500, self.poll)
        
    def do_unackcount(self, q, app, running_flag, lock):
        stopped = running_flag.is_set

        while not stopped():
            q.join()
            try:
                with lock:
                    value = app.getUnAckCount()
                q.put(value)
            except (OSError, URLError):  # socket errors
                pass
            except Exception as e:
                print("==========================")
                print("Error in UNACK thread")
                print_exc()
                print("==========================")
                q.put(False)

    def do_mainvalues(self, q, app, running_flag, lock):
        """
        @type q: Queue
        @return:
        """
        stopped = running_flag.is_set

        while not stopped():
            q.join()
            try:
                with lock:
                    values = app.getMainValues()
                q.put(values)
            except (OSError, URLError):  # socket errors
                pass
            except Exception as e:
                print("==========================")
                print("Error in AV thread", e)
                print("==========================")
                q.put(False)

    def get_mainvalues(self):
        try:
            rv = self.mvqueue.get(False)
        except Empty:
            rv = None
        else:
            self.mvqueue.task_done()
        return rv

    def do_advvalues(self, q, app, running_flag, lock):
        """
        @type q: Queue
        @return:
        """
        stopped = running_flag.is_set
        while not stopped():
            q.join()
            try:
                with lock:
                    values = app.getAdvancedValues()
                q.put(values)
            except (OSError, URLError):
                pass
            except Exception:
                print("==========================")
                print("Error in AV thread")
                print("==========================")
                q.put(False)

    def get_advvalues(self):
        try:
            rv = self.avqueue.get(False)
        except Empty:
            rv = None
        else:
            self.avqueue.task_done()
        return rv

    def update(self, update_widgets=True):

        if update_widgets:
            vars = self.vars
            mvc = self.mv_cont
            for group, params in self.main_values.items():
                vgroup = vars[group]
                mvg = mvc[group]
                for k, v in params.items():
                    if mvg[k] != v:
                        mvg[k] = v
                        vgroup[k][1].set(v)

            avvars = vars['Adv']
            avc = self.av_cont
            for k, v in self.adv_values.items():
                if avc[k] != v:
                    avc[k] = v
                    avvars[k][1].set(v)

        self.mframe.configure(text="MV: %d-%d, AV: %d-%d Alarms: %d" % (self.mvhb,
                                                                         self.mvbad,
                                                                         self.avhb,
                                                                         self.avbad,
                                                                         self.unack_count)
                            )

    def parse_adv_values2(self, dct):
        self.adv_values.update(dct)
        # cluster = root[1][0]
        # cluster = iter(cluster)
        # next(cluster)
        # next(cluster)
        # adv = self.adv_values
        # for elem in cluster:
        #     # print(elem)
        #     name = elem[0].text
        #     val = elem[1].text
        #     adv[name] = val

    def parse_main_values2(self, dct):
        # _next = next
        # _iter = iter
        #
        # cluster1 = root[1][0]
        # citer = _iter(cluster1)
        # _next(citer)
        # _next(citer)
        #
        # for group in citer:
        #     giter = _iter(group)
        #     gname = _next(giter).text
        #     _next(giter)
        #     vals = self.main_values[gname]
        #     for var in giter:
        #         vals[var[0].text] = var[1].text

        # unsure if dct.update() works recursively (deep copy). Probably not.
        for group_name, group_dct in dct.items():
            self.main_values[group_name].update(group_dct)

            
def main(ipv4):
    h = Hello(ipv4)
    h.mainloop()

if __name__ == '__main__':
    # xml_parse_call = lambda x: x

    from xml.etree.ElementTree import dump

    def dump(elem):
        if len(elem) > 0:
            for e in elem:
                dump(e)
            print(elem)
        else:
            print(elem, elem.text)

    ipv4 = '192.168.1.10'
    main(ipv4)

