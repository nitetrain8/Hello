# coding: utf-8

# In[1]:

ipv4 = '192.168.1.12'


# In[39]:

urlbase = 'http://%s/webservice/interface/?&' % ipv4


def setipv4(ipv4):
    global urlbase
    urlbase = "http://%s/webservice/interface/?&" % ipv4


# In[40]:

def coroutine(f):
    def func(*args, **kwargs):
        g = f(*args, **kwargs)
        next(g)
        return g.send

    return func


def coroutine2(f):
    def func(*args, **kwargs):
        g = f(*args, **kwargs)
        next(g)
        return g.__next__

    return func


# In[41]:

from urllib.request import urlopen, Request
from time import sleep, time


# In[42]:

headers = {}


def call_hello(url):
    req = Request(url, headers=headers)
    rsp = urlopen(req)
    rhdrs = rsp.getheaders()
    # print(rhdrs)
    for h, v in rhdrs:
        if h == 'Set-Cookie':
            headers['Cookie'] = v.split(';', 1)[0]
    return rsp

# In[59]:

from xml.etree.ElementTree import XML as xml_parse


class LoginError(Exception):
    pass


def login(user='user1', pwd='12345'):
    url = urlbase + "call=login&val1=%s&val2=%s&loader=Authenticating...&skipValidate=true" % (user, pwd)
    rsp = call_hello(url)
    txt = rsp.read().decode('utf-8')
    root = xml_parse(txt)
    msg = root[1]
    if msg.text != "True":
        raise LoginError("Bad login " + msg.text)
    return rsp


def setag(mode, val):
    url = urlbase + "call=set&group=agitation&mode=%s&val1=%f" % (mode, val)
    return call_hello(url)


def gmv():
    url = urlbase + "call=getMainValues&json=true"
    return call_hello(url)


def parsemv(mv):
    return loads(mv.read().decode('utf-8'))


def gpmv():
    return parsemv(gmv())['message']


# In[44]:
# if __name__ == '__main__':
# r = login()
#     r = login()


# In[45]:

#headers


# In[46]:

sps = 1, 2, 3, 4, 5, 10, 15, 20, 30, 40, 60, 80, 100


# In[47]:

from json import loads


def testrpm(sps=sps, st=120):
    rpms = {}
    for sp in sps:
        print("Renewing login...")
        login()
        print("Setting agitation to Manual, %f %% power" % sp)
        setag(1, sp)
        print("Sleeping %d seconds" % st)
        rpm = poll_mv(st, 'agitation', 'pv')
        print("Getting Main Values...")
        rsp = gmv().read()
        print("Parsing JSON")
        j = loads(rsp.decode())
        ag = j['message']['agitation']
        if float(ag['man']) != sp:
            raise ValueError("Oops", sp, ag['man'])
        rpms[sp] = rpm
        print("%d%% power <--> %s RPM\n" % (sp, rpm))
    print("Done.")
    return rpms


def poll_mv(t, group, name, interval=1, wait=30):
    _time = time  # LOAD_FAST v. LOAD_GLOBAL
    _sleep = sleep  # LOAD_FAST v. LOAD_GLOBAL
    now = _time()
    end = now + t
    vals = []
    append = vals.append  # eliminate GET_ATTR
    _sleep(wait)
    while True:

        mv = gmv()
        txt = mv.read().decode('utf-8')
        j = loads(txt)
        val = float(j['message'][group][name])
        append(val)

        if _time() > end:
            break

        _sleep(interval)

    return ave(vals)


def ave(ob):
    return sum(ob) / len(ob)


# In[48]:

#print('hi') 
#rpms = testrpm()


# In[49]:

def sort_rpms(rpms):
    return sorted(rpms.items(), key=lambda item: float(item[0]))


# In[63]:

#echo_on()
def plot_rpms(rpms, volume, bookname=None, column=1):
    from officelib.xllib.xladdress import cellRangeStr
    from officelib.xllib.xlcom import xlObjs, echo_on

    echo_on()
    xl, wb, ws, cells = xlObjs(bookname)

    rng = cellRangeStr((3, column), (len(rpms) + 2, column + 1))
    cells(2, column).Value = "Power"
    cells(2, column + 1).Value = "RPM"
    cells(2, 2 + column).Value = "Volume:"
    cells(3, 2 + column).Value = "%.2f" % volume
    cells.Range(rng).Value = rpms


def plot_30L():
    sps = 2.0, 4.0, 6.0, 8.0, 10.0
    rpms = testrpm(sps, 240)
    sorted_rpms = sort_rpms(rpms)
    plot_rpms(sorted_rpms, 30, 'LowVolumeRPM.xlsx', 1)


# In[65]:

def plot_25L():
    rpms_25L = testrpm(sps[::-1], 240)
    sorted_25L = sort_rpms(rpms_25L)
    plot_rpms(sorted_25L, 25, 'LowVolumeRPM.xlsx', 4)


# In[66]:

def plot_20L():
    rpms_20L = testrpm(sps[::-1], 240)
    sorted_20L = sort_rpms(rpms_20L)
    plot_rpms(sorted_20L, 20, 'LowVolumeRPM.xlsx', 7)


# In[72]:

def main2(st=120, vol=0, col=1):
    sps = 1, 2, 3, 4, 5, 8, 10, 15, 20, 25, 30, 35, 50, 60, 70, 80, 90
    rpms = testrpm(sps, st)
    sorted_rpms = sort_rpms(rpms)
    plot_rpms(sorted_rpms, vol, None, col)


# In[73]:

#main2()


# In[74]:

def getrpm100():
    setag(1, 100)
    rpm100 = poll_mv(120, 'agitation', 'pv')
    print(rpm100)
    return rpm100


# In[75]:

def getsprpm(sp, poll_time=120):
    setag(1, sp)
    return poll_mv(poll_time, 'agitation', 'pv')


# In[76]:

def mockpid(target):
    ipv4 = '192.168.1.84'
    setipv4(ipv4)
    sp = 100
    while True:
        login()
        setag(1, sp)
        pv = float(parsemv(gmv())['agitation']['pv'])
        if pv < target:
            return sp + 1
        sp -= 1


def testpid(p, i, sp, settle_time=60, margin=1, timeout=120):
    import sys

    pvs = []
    _time = time
    _sleep = sleep

    settle_min = sp - margin
    settle_max = sp + margin

    app.login()
    app.setconfig("Agitation", "P_Gain__(%25%2FRPM)", p)
    app.login()
    app.setconfig("Agitation", "I Time (min)", i)
    app.setag(0, sp)
    settle_end = _time() + settle_time

    print("Beginning Polling...")
    sys.stdout.flush()
    start = _time()
    end = _time() + timeout
    passed = True
    while True:

        pv = float(app.getagpv())
        pvs.append((_time() - start, pv))

        if not settle_min < pv < settle_max:
            t = _time()
            settle_end = t + settle_time
            if t > end:
                passed = False
                break

        elif _time() > settle_end:
            break

        _sleep(0.5)

    return passed, pvs


def plotpidtest(p, i, passed, rpms, wb, col):
    from officelib.xllib.xlcom import xlBook2

    xl, wb = xlBook2(wb)
    ws = wb.Worksheets(2)
    cells = ws.Cells
    xld = rpms
    cells(1, col).Value = "P:"
    cells(2, col).Value = "I:"
    cells(1, col + 1).Value = str(p)
    cells(2, col + 1).Value = str(i)
    cells(1, col + 2).Value = "Passed?"
    cells(2, col + 2).Value = ("No", "Yes")[passed]
    rng = cells.Range(cells(3, col), cells(len(xld) + 2, col + 1))
    rng.Value = xld


def manypidtests(settings, sp, wb, col=1, settle_time=60, margin=1):
    # I don't know if this is a good way to do this
    # it isn't.

    global app

    try:
        app
    except NameError:
        from hello.hello import HelloApp
        app = HelloApp('192.168.1.12')

    for p, i in settings:
        app.setag(2, 0)
        print("Testing: P: %.2f I: %.2f SP: %d" % (p, i, sp))
        passed, rpms = testpid(p, i, sp, settle_time, margin)
        t = PIDTest(p, i, passed, data=rpms)
        print("Plotting: P: %.2f I: %.2f SP: %d" % (p, i, sp))
        t.plotpidtest(wb, col)
        col += 4


class PIDTest():
    """ PID test container for tests run over
    9/12 - 9/14 weekend
    """

    _passmap = {
        "No": False,
        "Yes": True,
        True: True,
        False: False,
        1: True,
        0: False
    }

    def __init__(self, p, i, passed, xdata=None,
                 ydata=None, xrng=None, yrng=None, data=None):

        self.xrng = xrng
        self.yrng = yrng
        self.p = float(p)
        self.i = float(i)
        self.passed = self.parse_passed(passed)
        self.x = xdata
        self.y = ydata
        self.data = data

    def parse_passed(self, passed):
        """
        I should stop obsessively programming anti-dumbass features
        and just make sure not to be a dumbass.
        """
        return self._passmap[passed]

    def __repr__(self):
        return "P:%.2f I:%.2f Passed: %r" % (self.p, self.i, self.passed)

    __str__ = __repr__

    def chartplot(self, chart):
        from officelib.xllib.xlcom import CreateDataSeries
        CreateDataSeries(chart, self.xrng, self.yrng, repr(self))

    def createplot(self, ws):
        from officelib.xllib.xlcom import CreateChart, PurgeSeriesCollection
        chart = CreateChart(ws)
        PurgeSeriesCollection(chart)
        self.chartplot(chart)
        return chart

    def plotpidtest(self, wb_name, ws_num=1, col=1):

        if self.x and self.y:
            xld = [(x, y) for x, y in zip(self.x, self.y)]
        elif self.data:
            xld = self.data
        else:
            raise BadError("Can't plot- no data!")

        from officelib.xllib.xlcom import xlBook2
        from officelib.xllib.xladdress import cellRangeStr

        xl, wb = xlBook2(wb_name)
        ws = wb.Worksheets(ws_num)
        cells = ws.Cells

        # xrng and yrng not used in this function,
        # but we have the info here to calculate them
        # and preserve state
        xrng = cellRangeStr(
            (3, col),
            (2 + len(xld), col)
        )
        xrng = "=%s!%s" % (ws.Name, xrng)

        yrng = cellRangeStr(
            (3, col + 1),
            (2 + len(xld), col + 1)
        )

        yrng = "=%s!%s" % (ws.Name, yrng)

        self.xrng = xrng
        self.yrng = yrng

        cells(1, col).Value = "P:"
        cells(2, col).Value = "I:"
        cells(1, col + 1).Value = str(self.p)
        cells(2, col + 1).Value = str(self.i)
        cells(1, col + 2).Value = "Passed?"
        cells(2, col + 2).Value = ("No", "Yes")[self.passed]

        rng = cells.Range(cells(3, col), cells(len(xld) + 2, col + 1))
        rng.Value = xld


class BadError(Exception):
    pass


def parse_tests(wb_name):
    from officelib.xllib.xlcom import xlBook2
    from officelib.xllib.xladdress import cellRangeStr
    from officelib.const import xlDown

    xl, wb = xlBook2(wb_name)
    ws = wb.Worksheets(2)
    cells = ws.Cells
    crange = cells.Range

    col = 1
    tests = []
    while True:

        print("Scanning test in column %d...", col, end=' ')
        header = crange(cells(1, col), cells(2, col + 2)).Value
        _, p, _ = header[0]
        _, i, passed = header[1]

        n = 0
        for v in (p, i, passed):
            if v is None:
                n += 1

        if n == 3:
            break
        elif n > 0:
            raise BadError("Bad Data: p:%r i:%r passed:%r" % (p, i, passed))

        p = float(p)
        i = float(i)

        t = PIDTest(p, i, passed)

        xend = cells(3, col + 1).End(xlDown).Row
        xrng = cellRangeStr(
            (3, col),
            (xend, col)
        )

        yrng = cellRangeStr(
            (3, col + 1),
            (xend, col + 1)
        )

        xrng = "=%s!%s" % (ws.Name, xrng)
        yrng = "=%s!%s" % (ws.Name, yrng)

        t.xrng = xrng
        t.yrng = yrng

        if t.passed:

            data = crange(cells(3, col), cells(xend, col + 1)).Value
            xdata = []
            ydata = []
            for x, y in data:
                xdata.append(float(x))
                ydata.append(float(y))
            print("Got passing test!", end=' ')

        print("Done")

        tests.append(t)
        col += 4
    return tests


def plot_tests(ws, tests):
    cells = ws.Cells
    crange = cells.Range
    col = 1
    for t in tests:
        crange(cells(1, col), cells(2, col + 2)).Value = (
            ("P:", str(t.p), "Passed?"),
            "I:", str(t.i), str(t.passed)
        )

        data = []
        for x, y in zip(t.x, t.y):
            data.append((x, y))
        dlen = len(data)

        crange(cells(3, col), cells(2 + dlen, col + 1)).Value = data

        col += 4


def get_ranges(cells, col):
    from officelib.const import xlDown
    from officelib.xllib.xladdress import cellRangeStr

    header = cells.Range(cells(1, col), cells(2, col + 2))
    # data = cells.Range(cells(3, col), cells(cells(3, col + 1).End(xlDown).Row

    endrow = cells(3, col + 1).End(xlDown).Row
    xdata = cellRangeStr(
        (3, col),
        (endrow, col)
    )
    ydata = cellRangeStr(
        (3, col + 1),
        (endrow, col + 1)
    )

    return header, xdata, ydata


def parse_header(header):
    _, p, _ = header[0]
    _, i, passed = header[1]

    n = 0
    for v in (p, i, passed):
        if v is None:
            n += 1
    if 0 < n < 3:
        raise BadError("Bad Data: p:%r i:%r passed:%r" % (p, i, passed))

    if n == 3:
        return None, None, None, True

    p = float(p)
    i = float(i)

    return p, i, passed, False


def plot_many(wb_name, sheet_num):
    from officelib.xllib.xlcom import xlBook2, CreateChart, \
        PurgeSeriesCollection

    xl, wb = xlBook2(wb_name)
    ws = wb.Worksheets(sheet_num)
    cells = ws.Cells

    col = 1

    chart = CreateChart(ws)
    PurgeSeriesCollection(chart)

    while True:
        header, xdata, ydata = get_ranges(cells, col)
        col += 4

        p, i, passed, brk = parse_header(header)

        if brk:
            break

        xrng = "=%s!%s" % (ws.Name, xdata)
        yrng = "=%s!%s" % (ws.Name, ydata)
        t = PIDTest(p, i, passed, None, None, xrng, yrng)

        t.chartplot(chart)


