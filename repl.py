
from hello.ag_pid.poll import LowestTester, StartupPoller
from hello.ag_pid.agpid import SimplePIDRunner
from hello.ag_pid.poll import Poller


def _poll_overnight(p):
    # Poll
    p.poll()
    p.toxl()


def poll_overnight_2x200ohm_resistor():
    global po100r

    sps = (
    0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2, 2.5, 3, 3.5, 4, 4.5, 5,
    6, 7, 8, 9, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90,
    95, 100
    )[::-1]
    p = po100r = Poller(sps)

    _poll_overnight(p)

    return p


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


def doimports():
    import sys
    m = sys.modules['__main__']
    exec("from officelib.xllib.xlcom import xlObjs, xlBook2", m, m)
    exec("from hello.ag_pid.agpid import *", m, m)


def _set_meso_settings(r):
    r.set_setting("Agitation", "Auto Max Startup (%)", 0.2)
    r.set_setting("Agitation", "Power Auto Min (%)", 0.18)


def get_ovn_settings3():
    ps = 0.001, 0.002, 0.003, 0.005
    its = 0.005, 0.01, 0.02, 0.04
    ds = (0, 0.001, 0.005)
    sps = (15, 30, 45)

    return ps, its, ds, sps


def run_overnight_rnd():
    global rnd
    ps, its, ds, sps = get_ovn_settings3()
    rnd = SimplePIDRunner(ps, its, ds, sps, (), "AgPID RnD 10-2-14")
    _runagpid(rnd)
    return rnd


def run_overnight_meso():
    global meso
    ps, its, ds, sps = get_ovn_settings3()
    meso = SimplePIDRunner(ps, its, ds, sps, (), "AgPID Meso3 10-2-14", '192.168.1.16')
    _set_meso_settings(meso)
    _runagpid(meso)
    return meso


def run_over_weekend():
    p = 0.003
    i = 0.005
    d = 0.005
    sps = (10, 15, 20, 25)
    sps2 = (30, 35, 40)
    sps3 = (45, 50, 55)

    global r1, r2, r3
    r1 = SimplePIDRunner(p, i, d, sps)
    r2 = SimplePIDRunner(p, i, d, sps2)
    r3 = SimplePIDRunner(p, i, d, sps3)

    for r in (r1, r2, r3):
        try:
            _runagpid(r)
        except:
            print("Omg Error")
            import traceback
            print(traceback.format_exc())


def test_xl():
    r = SimplePIDRunner(0.003, 0.005, 0.005, 15)
    return r


def overnight_startup_lowest():
    global p, p2
    p = LowestTester()
    try:
        p.test_lowest(10, 10, 0.1, 60, 10)
        p.toxl()
    except:
        import traceback
        print(traceback.format_exc())

    p2 = StartupPoller()
    try:
        p2.test_startup(5, 10, 0.1, 20, 10, 60)
        p2.toxl()
    except:
        import traceback
        print(traceback.format_exc())

    return p, p2


def export(reports):
    path = "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\PBS 3 mech wheel\\"
    import datetime

    now = datetime.datetime.now().strftime("%m-%d-%y")
    filenames = []
    for name, id, r in reports:
        filename = "%s%s id-%d %s.csv" % (path, name, id, now)
        with open(filename, 'wb') as f:
            f.write(r)
        filenames.append(filename)
    return filenames


def kla_overnight(app=None, exps=None, volume=2):
    from hello.kla import KLATest
    from hello import HelloApp
    if exps is None:
        exps = [(0, sp, 200) for sp in range(10, 51, 10)]
        exps.append((0, 20, 500))

    global kt, batches
    global reports, results, batches
    if app is None:
        app = HelloApp("192.168.1.6")
    kt = KLATest(app)
    try:
        results = kt.run_experiments(volume, exps)
    except:
        raise
    else:
        batches = app.getbatches()
        reports = []
        for e in results:
            id = batches.getbatchid(e)
            r = app.getdatareport_bybatchid(id)
            reports.append((e, id, r))
        return export(reports)
    finally:
        # This ugly block make sure that DO is off after test no matter what
        # except for KeyboardInterrupt or SystemExit.
        while True:
            try:
                print("Attempting to shut off DO")
                app = HelloApp('192.168.1.6')
                if app.gpmv()['do']['mode'] != 2:
                    print("DO Wasn't off, logging in to turn it off")
                    app.login()
                    app.setdo(2, 0, 0)
                print("Yay")
                break
            except Exception:
                import traceback
                print("==========================================")
                print("ERROR SHUTTING DOWN TEST")
                print(traceback.format_exc())
                print("==========================================")


def analyze_batches(files=None, compiled_name="KLA Compiled Data"):
    import os
    from hello import kla
    pth = "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\PBS 3 mech wheel"
    if files is None:
        files = ['\\'.join((pth, f)) for f in os.listdir(pth)]
        files = [f for f in files if f.endswith('.csv') and 'kla' in f]
    analyzer = kla.KLAAnalyzer(files, pth + "\\", compiled_name)
    try:
        analyzer.analyze_all()
    finally:
        analyzer._xl.Visible = True


def kla2():
    files = kla_overnight(None, None, 3)
    analyze_batches(files)


def kla3():
    import pickle
    import subprocess
    subprocess.call("tskill.exe excel")
    with open("C:\\.replcache\\klaall11314.pkl", 'rb') as f:
        files2, files3 = pickle.load(f)

    # analyze_batches(files2, "KLA %dL Compiled Data" % 2)
    analyze_batches(files3, "KLA %dL Compiled Data" % 3)


def overnight3_settings():
    pl = [0.1 * x for x in range(1, 6)]
    il = [0.01 * x for x in range(1, 6)]
    dl = [0]  # no d for now
    sps = 8, 15, 30
    return pl, il, dl, sps


def run_overnight3():
    """
    overnight pid runner for PBS 80 Mesoblast I PID tuning.
    """
    pl, il, dl, sps = overnight3_settings()
    global ovn3_runner
    ipv4 = "192.168.1.fixme"
    ovn3_runner = SimplePIDRunner(pl, il, dl, sps, app_or_ipv4=ipv4)
    try:
        _runagpid(ovn3_runner)
    except:
        print("OMG Error")
        import traceback
        print(traceback.format_exc())



if __name__ == '__main__':
    # from hello import HelloApp
    # app = HelloApp("192.168.1.6")
    # r = app.getdoravalues()
    # print(r)
    pass


