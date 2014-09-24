import hello.ag_pid_test_issue2033 as agpid
from time import sleep
gmv = agpid.gmv
parsemv = agpid.parsemv


def setag(mode, sp, log=True):
    modes = ("Auto", "Manual", "Off")
    agpid.login()
    if log is True:
        print("Setting agitation to %s %.1f%% power..." % (modes[mode], sp), end='')
    rsp = agpid.setag(mode, sp)
    if log is True:
        print(" Done")
    return rsp


def testag(start, end, step=1, t=20):
    try:
        for sp in range(start, end, step):
            setag(1, sp)
            sleep(t)
    except KeyboardInterrupt:
        return


def teststart(start, end, step, t=5):
    sp = start
    try:
        setag(1, 0)
        sleep(3)
        while sp <= end:
            setag(1, sp)
            sleep(t)
            setag(1, 0)
            sleep(3)
            sp += step
    except KeyboardInterrupt:
        pass
    return sp


def teststart2(start, end, step, t=5, iters=3):
    sps = []
    for _ in range(iters):
        sp = teststart(start, end, step, t)
        sps.append(sp)
    return ave(sps), sps


def getagpv():
    return float(parsemv(gmv())['message']['agitation']['pv'])


def init_low_poll(start, end, step, t):
    sp = start
    while True:
        setag(1, sp, False)
        sp -= step
        if sp < end:
            break
        sleep(t)


def poll_lowest(sp, step, t):
    polling = True
    while polling:
        polling = False
        init_low_poll(15, sp + 1, .5, .5)
        init_low_poll(sp + 2, sp, .1, 1)
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
        init_low_poll(10, sp, 1, 1)
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
    return sum(o) / len(o)


def testlowest2(sp, step, t=20, iters=3):
    pvs = []
    for _ in range(iters):
        sp, pv = testlowest(sp, step, t)
        pvs.append(pv)
    return ave(pvs), pvs


def init_high_poll(sp, end, step=1.0, t=1.0):
    while True:
        setag(1, sp, False)
        sp += step
        if sp > end:
            break
        sleep(t)


def testhighest2(sp, step, t=5, iters=3):
    pvs = []
    for _ in range(iters):
        sp, pv = testhighest(sp, step, t)
        pvs.append(pv)

    return ave(pvs), pvs


def testhighest(start, step, t=5):
    sp = start
    setag(1, sp, True)
    sp += step
    ag = pv = getagpv()
    while sp <= 100:
        setag(1, sp, True)
        sleep(t)
        pv = getagpv()
        if pv < 0.9 * ag:
            sp -= step
            break
        sp += step
        ag = pv
    return poll_highest(sp - step, step, 30)


def poll_highest(sp, step, t):
    polling = True
    while polling:
        polling = False
        st = t * 2

        initsp = max(15, sp - 10)
        init_high_poll(15, initsp, 2, 2)
        # setag(1, sp)
        sleep(10)
        st -= 10

        # this is kind of sloppy, but basically keep track of
        # some pv value before we finish initializing the high
        # poll value to act as a sentinel to compare against to
        # determine whether the wheel stopped.
        warningpv = getagpv()

        if 0 == warningpv:
            polling = True
            sp -= step
            continue

        init_high_poll(initsp, sp, 1, 1)

        setag(1, sp)
        sleep(30)
        st -= 30

        while st > 0:
            ag = getagpv()
            if ag < warningpv:
                print("Oops! Ag stopped, decreasing setpoint")
                sp -= step
                polling = True
                break
            sleep(1)
            st -= 1

    ag = getagpv()
    print("Maximum RPM: %.2f%% <-> %.2f" % (sp, ag))

    return sp, ag
