from hello.hello import HelloApp
import sys
import random

output = sys.stdout.write

def spam_hello_gmv(app):
    coro = spam_hello_gmv_coro(app)
    i = 1
    while True:
        try:
            next(coro)
        except (KeyboardInterrupt, StopIteration):
            return
        output("\rSpamming GMV: %d" % i)
        i += 1
        
def spam_hello_set(app):
    coro = spam_hello_set_coro(app)
    while True:
        try:
            next(coro)
        except (KeyboardInterrupt, StopIteration):
            return
        
def spam_hello_set_coro(app):
    from random import random, choice
    
    getrand = lambda: [random() * 30]
    getrand2 = lambda: [random() * 30, random() * 30]
    
    cs = []
    for func in (app.setag, app.settemp):
        for mode in (0, 1, 2):
            cs.append((func, mode, getrand))
    
    for func in (app.setph, app.setdo):
        cs.append((func, 1, getrand2))
        for mode in (0, 2):
            cs.append((func, mode, getrand))
        
    app.login()
    i = 1
    try:
        while True:
            fn, mode, argfunc = choice(cs)
            args = argfunc()
            output("\rSpamming Hello with set: %d" % i)
            fn(mode, *args)
            yield
            
    except KeyboardInterrupt:
        pass

def spam_hello_gmv_coro(app):
    while True:
        app.getMainValues()
        yield
        
def spam_hello_gettrenddata_coro(app):
        spans = "15min", "2hr", "12hr", "24hr", "72hr", "7day"
        groups = "agitation", "ph", "do", "temperature"
        combos = [(s, g) for s in spans for g in groups]
        while True:
            g, s = random.choice(combos)
            app.getTrendData(g, s)
            yield
            
def spam_hello_getconfig_coro(app):
    while True:
        app.getConfig()
        yield
        
def spam_hello_gdv_coro(app):
    while True:
        app.getDORAValues()
        yield
        
def spam_hello_getalarms_coro(app):
    while True:
        app.getAlarms()
        yield        
        
def random_choice_from_dict(d):
    key = random.choice(list(d))
    value = d[key]
    return key, value
    
def spam_hello_setconfig_coro(app, output=output):
    settings = app.getConfig()
    groups = list(settings)
    g_len = len(groups)
    names = [list(settings[g]) for g in groups]
    
    combos = []
    for i, g in enumerate(groups):
        for name in names[i]:
            combos.append((g, name))
    app.login()
    try:
        while True:
            grp, name = random.choice(combos)
            val = random.random() * 30
            output("\r                                                ")
            output("\rSetting config: %s:%s = %.5f" % (grp, name, val))
            app.setconfig(grp, name, val)
            yield
    finally:
        while True:
            try:
                app.login()
                while combos:
                    grp, name = combos[-1]
                    val = settings[grp][name]
                    output("Restoring config: %s:%s = %s\n" % (grp, name, val))
                    app.setconfig(grp, name, val)
                    del combos[-1]
            except:
                continue
            else:
                break
                
def ensure(func):
    while True:
        try:
            func()
        except:
            pass
        else:
            break
    
        
class HelloSpamCoroRunner():
    
    def __init__(self, app, coros):
        self.app = app
        self.coros = coros
    
    def run_forever(self):
        i = 1
        try:
            while True:
                for c in self.coros:
                    next(c)
                    output("\r                                                                  ")
                    output("\rSpamming lots of hello: %d" % i)
                i += 1
        finally:
            for c in self.coros:
                try:
                    c.throw(StopIteration)
                except StopIteration:
                    pass
    
    spam = run_forever
                
class HelloSpamAll(HelloSpamCoroRunner):
    def __init__(self, app):
        gmv = spam_hello_gmv_coro(app)
        set_ = spam_hello_set_coro(app)
        cfg = spam_hello_getconfig_coro(app)
        alarms = spam_hello_getalarms_coro(app)
        dra = spam_hello_gdv_coro(app)
        td = spam_hello_gettrenddata_coro(app)
        sc = spam_hello_setconfig_coro(app)
        super().__init__(app, (gmv, set_, cfg, alarms, dra, td, sc))
        
def spam_all(ipv4):
    app = HelloApp(ipv4)
    spammer = HelloSpamAll(app)
    spammer.spam()
        