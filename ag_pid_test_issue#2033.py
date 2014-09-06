
# coding: utf-8

# In[48]:

ipv4 = '192.168.1.7'


# In[49]:

url = 'http://%s/webservice/interface/?&' % ipv4


# In[50]:

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


# In[51]:

from urllib.request import urlopen, Request
from time import sleep, time


# In[52]:

headers = {}

def call_hello(url):

    req = Request(url, headers=headers)
    rsp = urlopen(req)
    rhdrs = rsp.getheaders()
    #print(rhdrs)
    for h, v in rhdrs:
        if h == 'Set-Cookie':
            headers['Cookie'] = v.split(';', 1)[0]
    return rsp
        


# In[53]:

from xml.etree.ElementTree import XML as xml_parse

class LoginError(Exception):
    pass

def login(user='user1', pwd='12345'):
    url = "http://192.168.1.2/webservice/interface/?&call=login&val1=%s&val2=%s&loader=Authenticating...&skipValidate=true" % (user, pwd)
    rsp = call_hello(url)
    txt = rsp.read().decode('utf-8')
    root = xml_parse(txt)
    msg = root[1]
    if msg.text != "True":
        raise LoginError("Bad login " + msg.text)
    return rsp
    
    

def setag(mode, val):
    url = "http://192.168.1.2/webservice/interface/?&call=set&group=agitation&mode=%s&val1=%f" % (mode, val)
    return call_hello(url)

def gmv():
    url = "http://192.168.1.2/webservice/interface/?&call=getMainValues&json=true"
    return call_hello(url)


# In[54]:

r = login()
r = login()


# In[55]:

#headers


# In[56]:

sps = 1, 2, 3, 4, 5, 10, 15, 20, 30, 40, 60, 80, 100


# In[57]:

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


def poll_mv(t, group, name, interval=1):
    _time = time  # LOAD_FAST v. LOAD_GLOBAL
    _sleep = sleep  # LOAD_FAST v. LOAD_GLOBAL
    now = _time()
    end = now + t
    vals = []; append = vals.append  # eliminate GET_ATTR
    _sleep(30)
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
    


# In[58]:

#print('hi') 
#rpms = testrpm()


# In[59]:

def sort_rpms(rpms):
    return sorted(rpms.items(), key=lambda item: float(item[0]))


# In[69]:

from officelib.xllib.xlcom import xlObjs, echo_on, echo_off
echo_on()
from officelib.xllib.xladdress import cellRangeStr


def plot_rpms(rpms, volume, bookname=None, column=1):
    xl, wb, ws, cells = xlObjs(bookname)
    rng = cellRangeStr((3, column), (len(rpms)+2, column+1))
    cells(2, 3 + column).Value = "Volume:"
    cells(3, 3 + column).Value = "%.2f" % volume 
    cells.Range(rng).Value = rpms


# In[61]:

#plot_rpms(sorted_rpms, 'Book5')


# In[62]:
def main():
    sps = 2.0, 4.0, 6.0, 8.0, 10.0
    rpms = testrpm(sps, 240)
    sorted_rpms = sort_rpms(rpms)
    plot_rpms(sorted_rpms, 2, 'LowVolumeRPM.xlsx', 1)


    # In[67]:

    plot_rpms(sorted_rpms, 30, 'LowVolumeRPM.xlsx', 1)


    # In[68]:

    rpms_25L = testrpm(sps[::-1], 240)
    sorted_25L = sort_rpms(rpms_25L)
    plot_rpms(sorted_25L, 25, 'LowVolumeRPM.xlsx', 4)


    # In[71]:

    rpms_20L = testrpm(sps[::-1], 240)
    sorted_20L = sort_rpms(rpms_20L)
    plot_rpms(sorted_20L, 20, 'LowVolumeRPM.xlsx', 7)


    # In[ ]:

def main2():
    sps = 1, 2, 3, 4, 5, 8, 10, 15, 20, 25, 30, 35, 50, 60, 70, 80, 90
    rpms = testrpm(sps)
    sorted_rpms = sort_rpms(rpms)
    plot_rpms(sorted_rpms, 2.5, None, 1)




