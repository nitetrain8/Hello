def setag(mode, sp, log=True):
    agpid.login()
    if log:
        print("Setting agitation to %.1f..." % sp, end='')
    rsp = agpid.setag(mode, sp)
    if log:
        print(" Done")
    return rsp


def testag(start, end, step=1, t=20):
    try:
        for sp in range(start, end, step):
            setag(1, sp)
            sleep(t)
    except KeyboardInterrupt:
        return

def teststart(start, end, t=5):
    try:
        setag(1, 0)
        sleep(3)
        for sp in range(start, end+1):
            setag(1, sp)
            sleep(t)
            setag(1, 0)
            sleep(3)
    except KeyboardInterrupt:
        return

def getagpv():
    return float(parsemv(gmv())['message']['agitation']['pv'])


def init_poll(sp, end, step, t):

    while sp > end:
        setag(1, sp, False)
        sp -= step
        sleep(1)

def poll_lowest(sp, step, t):
    polling = True
    while polling:
        polling = False
        init_poll(15, sp + 1, .5, .5)
        init_poll(sp + 2, sp, .1, 1)
        setag(1, sp)
        st = t * 2
        sleep(20)
        st -= 20
        while st > 0:
            ag = getagpv()
            if 0 == ag:
                print("Oops! Ag stopped, increasing setpoint")
                sp += step
                polling = True
                break
            sleep(1)
            st -= 1
    ag = getagpv()
    print("Minimum RPM: %.2f%% <-> %.2f" % (sp, ag))
    return sp, ag


def testlowest(sp, step, t):
    try:
        init_poll(10, sp, 1, 1)
        while True:
            try:
                setag(1, sp)
                sleep(t)
                ag = getagpv()
                if 0 == ag:
                    break
                sp -= step
            except KeyboardInterrupt:
                rsp = input("Continue?")
                if rsp and rsp in "Yy":
                    sp -= step
                else:
                    raise
        sp += step
        print("Found minimum setpoint: %.2f" % sp)
        return poll_lowest(sp, step, t)
    except KeyboardInterrupt:
        return "Incomplete"

def ave(o):
    return sum(o)/len(o)

def testlowest2(sp, step, t=20, iters=3):
    pvs = []
    for _ in range(iters):
        sp, pv = testlowest(sp, step, t)
        pvs.append(pv)
    return ave(pvs), pvs

