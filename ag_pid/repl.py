
from hello.ag_pid.agpid import SimplePIDRunner
from hello.ag_pid.poll import Poller


def _poll_overnight(plr):
    # Poll

    plr.poll()
    plr.toxl()


def _runagpid(r):
    """
    @type r: SimplePIDRunner
    """
    r.runall()
    r.plotall()
    r.chartbypid()
    r.close()
    return r


def run_overnight2():
    global p, r, r2
    sps = (
        0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2, 2.5, 3, 3.5, 4, 4.5, 5,
        6, 7, 8, 9, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90,
        95, 100
    )
    p = Poller(sps)

    pgains1 = (0.02, 0.03, 0.04, 0.05)
    itimes1 = (0.001, 0.005, 0.01, 0.015)
    dtimes1 = (0,)
    sps = 15, 25, 45

    r = SimplePIDRunner(pgains1, itimes1, dtimes1, sps)

    dtimes2 = 0.0001, 0.0005, 0.001, 0.005, 0.01

    r2 = SimplePIDRunner(pgains1, itimes1, dtimes2, sps)

    gv = globals().values()

    assert p in gv
    assert r in gv
    assert r2 in gv

    _poll_overnight(p)
    _runagpid(r)
    _runagpid(r2)
    return p, r, r2


def test_really_fast():
    global sps, p
    sps = (
        # 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4,
        1.6, 1.8, 2, 2.5, 3, 3.5, 4, 4.5, 5,
        6, 7, 8, 9, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75
    )[::-1]
    p = Poller(sps, 40, 120)
    p._log_name = "Pow v RPM resist before cap"
    try:
        _poll_overnight(p)
    except:
        import traceback
        traceback.print_exc()
    return p


def test_really_fast2():
    global p, p2

    sps = tuple(range(80, 101, 5))

    p2 = Poller(sps, 40, 120)
    p2._results = p._results.copy()

    try:
        _poll_overnight(p2)
    except:
        import traceback
        traceback.print_exc()
    return p2

