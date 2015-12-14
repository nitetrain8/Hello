# try:
#     from hello.ag_pid.poll import LowestTester, StartupPoller
#     from hello.ag_pid.agpid import SimplePIDRunner
#     from hello.ag_pid.poll import Poller
#     from hello.hello import HelloApp
# except ImportError:
#     from ag_pid.poll import LowestTester, StartupPoller
#     from ag_pid.agpid import SimplePIDRunner
#     from ag_pid.poll import Poller
#     from hello import HelloApp
#
# from time import sleep
#
#
# def run_poll(p):
#     # Poll
#     p.poll()
#     p.toxl()
#
#
# def poll_overnight_2x200ohm_resistor():
#     global po100r
#
#     sps = (
#     0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2, 2.5, 3, 3.5, 4, 4.5, 5,
#     6, 7, 8, 9, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90,
#     95, 100
#     )[::-1]
#     p = po100r = Poller(sps)
#
#     run_poll(p)
#
#     return p
#
#
# def _runagpid(r):
#     """
#     @type r: SimplePIDRunner
#     """
#     r.runall()
#     r.plotall()
#     r.chartbypid()
#     r.close()
#     return r
#
#
# def run_overnight2():
#     global p, r, r2
#     sps = (
#         0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6, 1.8, 2, 2.5, 3, 3.5, 4, 4.5, 5,
#         6, 7, 8, 9, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90,
#         95, 100
#     )
#     p = Poller(sps)
#
#     pgains1 = (0.02, 0.03, 0.04, 0.05)
#     itimes1 = (0.001, 0.005, 0.01, 0.015)
#     dtimes1 = (0,)
#     sps = 15, 25, 45
#
#     r = SimplePIDRunner(pgains1, itimes1, dtimes1, sps)
#
#     dtimes2 = 0.0001, 0.0005, 0.001, 0.005, 0.01
#
#     r2 = SimplePIDRunner(pgains1, itimes1, dtimes2, sps)
#
#     gv = globals().values()
#
#     assert p in gv
#     assert r in gv
#     assert r2 in gv
#
#     run_poll(p)
#     _runagpid(r)
#     _runagpid(r2)
#     return p, r, r2
#
#
# def test_really_fast():
#     global sps, p
#     sps = (
#         # 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4,
#         1.6, 1.8, 2, 2.5, 3, 3.5, 4, 4.5, 5,
#         6, 7, 8, 9, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75
#     )[::-1]
#     p = Poller(sps, 40, 120)
#     p._log_name = "Pow v RPM resist before cap"
#     try:
#         run_poll(p)
#     except:
#         import traceback
#         traceback.print_exc()
#     return p
#
#
# def test_really_fast2():
#     global p, p2
#
#     sps = tuple(range(80, 101, 5))
#
#     p2 = Poller(sps, 40, 120)
#     p2._results = p._results.copy()
#
#     try:
#         run_poll(p2)
#     except:
#         import traceback
#         traceback.print_exc()
#     return p2
#
#
# def doimports():
#     import sys
#     m = sys.modules['__main__']
#     exec("from officelib.xllib.xlcom import xlObjs, xlBook2", m, m)
#     exec("from hello.ag_pid.agpid import *", m, m)
#
#
# def _set_meso_settings(r):
#     r.set_setting("Agitation", "Auto Max Startup (%)", 0.2)
#     r.set_setting("Agitation", "Power Auto Min (%)", 0.18)
#
#
# def get_ovn_settings3():
#     ps = 0.001, 0.002, 0.003, 0.005
#     its = 0.005, 0.01, 0.02, 0.04
#     ds = (0, 0.001, 0.005)
#     sps = (15, 30, 45)
#
#     return ps, its, ds, sps
#
#
# def run_overnight_rnd():
#     global rnd
#     ps, its, ds, sps = get_ovn_settings3()
#     rnd = SimplePIDRunner(ps, its, ds, sps, (), "AgPID RnD 10-2-14")
#     _runagpid(rnd)
#     return rnd
#
#
# def run_overnight_meso():
#     global meso
#     ps, its, ds, sps = get_ovn_settings3()
#     meso = SimplePIDRunner(ps, its, ds, sps, (), "AgPID Meso3 10-2-14", '192.168.1.16')
#     _set_meso_settings(meso)
#     _runagpid(meso)
#     return meso
#
#
# def run_over_weekend():
#     p = 0.003
#     i = 0.005
#     d = 0.005
#     sps = (10, 15, 20, 25)
#     sps2 = (30, 35, 40)
#     sps3 = (45, 50, 55)
#
#     global r1, r2, r3
#     r1 = SimplePIDRunner(p, i, d, sps)
#     r2 = SimplePIDRunner(p, i, d, sps2)
#     r3 = SimplePIDRunner(p, i, d, sps3)
#
#     for r in (r1, r2, r3):
#         try:
#             _runagpid(r)
#         except:
#             print("Omg Error")
#             import traceback
#             print(traceback.format_exc())
#
#
# def test_xl():
#     r = SimplePIDRunner(0.003, 0.005, 0.005, 15)
#     return r
#
#
# def overnight_startup_lowest():
#     global p, p2
#     p = LowestTester()
#     try:
#         p.test_lowest(10, 10, 0.1, 60, 10)
#         p.toxl()
#     except:
#         import traceback
#         print(traceback.format_exc())
#
#     p2 = StartupPoller()
#     try:
#         p2.test_startup(5, 10, 0.1, 20, 10, 60)
#         p2.toxl()
#     except:
#         import traceback
#         print(traceback.format_exc())
#
#     return p, p2
#
#
# def export(reports):
#     path = "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\PBS 3 mech wheel\\"
#     import datetime
#
#     now = datetime.datetime.now().strftime("%m-%d-%y")
#     filenames = []
#     for name, id, r in reports:
#         filename = "%s%s id-%d %s.csv" % (path, name, id, now)
#         with open(filename, 'wb') as f:
#             f.write(r)
#         filenames.append(filename)
#     return filenames
#
#
# def kla_overnight(app=None, exps=None, volume=2):
#     from hello.kla import MechKLATest
#     from hello import HelloApp
#     if exps is None:
#         exps = [(0, sp, 200) for sp in range(10, 51, 10)]
#         exps.append((0, 20, 500))
#
#     global kt, batches
#     global reports, results, batches
#     if app is None:
#         app = HelloApp("192.168.1.6")
#     kt = MechKLATest(app)
#     try:
#         results = kt.run_experiments(volume, exps)
#     except:
#         raise
#     else:
#         batches = app.getBatches()
#         reports = []
#         for e in results:
#             id = batches.getbatchid(e)
#             r = app.getdatareport_bybatchid(id)
#             reports.append((e, id, r))
#         return export(reports)
#     finally:
#         # This ugly block make sure that DO is off after test no matter what
#         # except for KeyboardInterrupt or SystemExit.
#         while True:
#             try:
#                 print("Attempting to shut off DO")
#                 app = HelloApp('192.168.1.6')
#                 if app.gpmv()['do']['mode'] != 2:
#                     print("DO Wasn't off, logging in to turn it off")
#                     app.login()
#                     app.setdo(2, 0, 0)
#                 print("Yay")
#                 break
#             except Exception:
#                 import traceback
#                 print("==========================================")
#                 print("ERROR SHUTTING DOWN TEST")
#                 print(traceback.format_exc())
#                 print("==========================================")
#
#
# def analyze_batches(files=None, compiled_name="KLA Compiled Data"):
#     import os
#     from hello import kla
#     pth = "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\PBS 3 mech wheel"
#     if files is None:
#         files = ['\\'.join((pth, f)) for f in os.listdir(pth)]
#         files = [f for f in files if f.endswith('.csv') and 'kla' in f]
#     analyzer = kla.KLAAnalyzer(files, pth + "\\", compiled_name)
#     try:
#         analyzer.analyze_all()
#     finally:
#         analyzer._xl.Visible = True
#
#
# def kla2():
#     files = kla_overnight(None, None, 3)
#     analyze_batches(files)
#
#
# def kla3():
#     import pickle
#     import subprocess
#     subprocess.call("tskill.exe excel")
#     with open("C:\\.replcache\\klaall11314.pkl", 'rb') as f:
#         # noinspection PyArgumentList
#         files2, files3 = pickle.load(f)
#
#     # analyze_batches(files2, "KLA %dL Compiled Data" % 2)
#     analyze_batches(files3, "KLA %dL Compiled Data" % 3)
#
#
# def overnight3_settings():
#     pl = [0.1 * x for x in range(1, 6)]
#     il = [0.01 * x for x in range(1, 6)]
#     dl = [0]  # no d for now
#     sps = 8, 15, 30
#     return pl, il, dl, sps
#
#
# def run_overnight3():
#     """
#     overnight pid runner for PBS 80 Mesoblast I PID tuning.
#     """
#     pl, il, dl, sps = overnight3_settings()
#     global ovn3_runner
#     ipv4 = "192.168.1.fixme"
#     ovn3_runner = SimplePIDRunner(pl, il, dl, sps, app_or_ipv4=ipv4)
#     try:
#         _runagpid(ovn3_runner)
#     except:
#         print("OMG Error")
#         import traceback
#         print(traceback.format_exc())
#
#
# def init_pon3_sps():
#     sps = []
#     sps.extend(i for i in range(1, 10))
#     sps.reverse()
#     sps.extend(i for i in range(10, 20, 2))
#     sps.extend(i for i in range(20, 101, 5))
#     return sps
#
#
# def PBS_80_Mesoblast_I_poll1(app=None):
#     """ For PBS 80 Mesoblast I """
#     global p
#     if app is None:
#         from hello.hello import HelloApp
#         app = HelloApp('192.168.1.4')
#     sps = init_pon3_sps()
#     p = Poller(sps, 40, 120, app)
#     p.set_logname("Pow v RPM PBS 80 Mesoblast I")
#     try:
#         run_poll(p)
#     except:
#         import traceback
#         traceback.print_exc()
#     return p
#
#
# def pid_overnight_150129(app):
#     """ For PBS 80 Mesoblast I """
#     global r
#     ps = [0.1 * i for i in range(1, 7)]
#     its = [0.05 * i for i in range(1, 11)]
#     sps = 5, 10, 15, 20, 25, 30
#     try:
#         r = SimplePIDRunner(ps, its, (0,), sps, app_or_ipv4=app)
#         _runagpid(r)
#     except:
#         import traceback
#         traceback.print_exc()
#     return r
#
#
# def overnight_150129():
#     """
#     For Mesoblast 80L power curve + ag PID
#     """
#     from hello.hello import HelloApp
#     app = HelloApp('192.168.1.4')
#     rs = []
#     for fn in (PBS_80_Mesoblast_I_poll1, pid_overnight_150129):
#         try:
#             rv = fn(app)
#             rs.append(rv)
#         finally:
#             app.login()
#             app.setag(0, 25)
#             app.setdo(1, 20, 250)
#             app.setph(1, 20, 0)
#             app.setmg(1, 10)
#             app.settemp(0, 37)
#     return rs
#
#
# def init_pon3_sps2():
#     sps = []
#     sps.extend(i for i in range(10, 20, 10))
#     sps.extend(i for i in range(20, 101, 10))
#     return sps
#
#
# def PBS_80_Mesoblast_I_poll2(app=None):
#     """ For PBS 80 Mesoblast I """
#     global p
#     if app is None:
#         from hello.hello import HelloApp
#         app = HelloApp('192.168.1.4')
#     sps = init_pon3_sps2()
#     p = Poller(sps, 20, 20, app)
#     p.set_logname("Pow v RPM PBS 80 Mesoblast I")
#     try:
#         run_poll(p)
#     except:
#         import traceback
#         traceback.print_exc()
#     return p
#
#
# def really_fast_test_new_wheel_endcaps(ipv4='192.168.1.4'):
#     """
#     For Mesoblast 80L power curve + ag PID
#     """
#     from hello.hello import HelloApp
#     app = HelloApp(ipv4)
#
#     try:
#         rv = PBS_80_Mesoblast_I_poll2(app)
#     finally:
#         app.login()
#         app.setag(0, 25)
#         app.setdo(1, 20, 250)
#         app.setph(1, 20, 0)
#         app.setmg(1, 10)
#         app.settemp(0, 37)
#     return rv
#
#
# def over_weekend_150130(ipv4='192.168.1.4'):
#     from hello.hello import HelloApp
#     from hello.temp_pid.temppid import Runner
#
#     ps = (30, 40, 50)
#     its = 10, 15, 20
#     ds = 0,
#     sps = 37,
#
#     app = HelloApp(ipv4)
#     runner = Runner(ps, its, ds, sps, app)
#     try:
#         runner.runall()
#         runner.plotall()
#     finally:
#         app.setag(0, 28)
#         app.settemp(0, 37)
#
#
# def power_curve_pbs3dyncI():
#     global sps, p
#     sps = tuple(range(10, 101, 10))[::-1]
#     p = Poller(sps, 40, 60, '192.168.1.11')
#     p.set_logname("PBS 3 dync I Power Curve")
#     try:
#         run_poll(p)
#     except:
#         import traceback
#         traceback.print_exc()
#     return p
#
#
# def power_curve_pbs3BetaLogicsI():
#     """
#     Power curve for PBS 3 betalogics i- brush motor with no cap
#     """
#     global sps, p
#     sps = tuple(range(1, 101, 1))[::-1]
#     app = HelloApp("192.168.1.9")
#     app.login()
#     for sp in range(10, 101, 10):
#         app.setag(1, sp)
#         sleep(1)
#     p = Poller(sps, 40, 60, app)
#     p.set_logname("PBS 3 BetaLogics I Power Curve")
#     try:
#         run_poll(p)
#     except:
#         import traceback
#         traceback.print_exc()
#     return p
#
#
#
# def brush_motor_nocap_settings():
#     pl = (.01, .02, .03, .04, .05)
#     il = (0.005,)
#     dl = [0]  # no d for now
#     sps = 8, 15, 30
#     return pl, il, dl, sps
#
#
# def pid_test_brush_nocap():
#     """
#     overnight pid runner for PBS 80 Mesoblast I PID tuning.
#     """
#     global runner
#     pl, il, dl, sps = brush_motor_nocap_settings()
#     ipv4 = "192.168.1.9"
#     runner = SimplePIDRunner(pl, il, dl, sps, app_or_ipv4=ipv4)
#     runner.set_setting("Agitation", "Auto Max Startup (%)", 5)
#     try:
#         _runagpid(runner)
#     except:
#         print("OMG Error")
#         import traceback
#         print(traceback.format_exc())
#
# def brush_motor_nocap_settings2():
#     pl = (.008, .01, .012)
#     il = (0.005,)
#     dl = [0]  # no d for now
#     sps = 8, 15, 30, 45
#     return pl, il, dl, sps
#
#
# def pid_test_brush_nocap2():
#     """
#     overnight pid runner for PBS 80 Mesoblast I PID tuning.
#     """
#     global runner
#     pl, il, dl, sps = brush_motor_nocap_settings2()
#     ipv4 = "192.168.1.9"
#     runner = SimplePIDRunner(pl, il, dl, sps, app_or_ipv4=ipv4)
#     runner.set_setting("Agitation", "Auto Max Startup (%)", 3)
#     try:
#         _runagpid(runner)
#     except:
#         print("OMG Error")
#         import traceback
#         print(traceback.format_exc())
#
#
# def brushless_motor_settings():
#     pl = (.3, .6, .9)
#     il = (0.01, .005, .001)
#     dl = [0]  # no d for now
#     sps = 8, 15, 30, 45
#     return pl, il, dl, sps
#
#
# def pid_test_brushless():
#     global runner
#     pl, il, dl, sps = brushless_motor_settings()
#     ipv4 = "71.189.82.196:82"
#     runner = SimplePIDRunner(pl, il, dl, sps, app_or_ipv4=ipv4)
#     runner.set_setting("Agitation", "Auto Max Startup (%)", 10)
#     runner.set_setting("Agitation", "Power Auto Min (%)", 0.1)
#
#     try:
#         _runagpid(runner)
#     except:
#         print("OMG Error")
#         import traceback
#         print(traceback.format_exc())
#
#
# def power_curve_brushless(ipv4="71.189.82.196:82"):
#     """
#     Power curve for PBS 3 betalogics i- brush motor with no cap
#     """
#     global sps, p
#     sps = tuple(range(10, 101, 10))[::-1]
#     app = HelloApp(ipv4)
#     app.login()
#     for sp in range(10, 101, 10):
#         app.setag(1, sp)
#         sleep(1)
#     p = Poller(sps, 20, 20, app)
#     p.set_logname("PBS 3 Brushless Motor")
#     try:
#         run_poll(p)
#     except:
#         import traceback
#         traceback.print_exc()
#     return p
#
# def power_curve_betalogics_troubleshoot():
#     global sps, p
#     sps = 100, 80, 60, 50, 40, 30, 20, 10, 8, 6, 5, 4, 3
#     # app = Hello
#


# def kla_load_from_file():
#     """
#     for MIC-TR-2-008
#     """
#     try:
#         from hello import kla
#     except ImportError:
#         import kla
#
#     rc = kla.KLAReactorContext(0.5, 0.5, 0.5, 0.3, 0.02, 0.5, 4, 1, 30, 25, 20)
#     tc = kla.KLATestContext(7, 5, 6)
#     # tc = kla.KLATestContext(1, 0.1, 20)
#     r = kla.AirKLATestRunner("71.189.82.196:6", rc, tc)
#
#     filepath = "C:\\Users\\PBS Biotech\\Downloads\\MIC-TR-X-008a.csv"
#     with open(filepath, 'r') as f:
#         f.readline()  # discard header
#
#         for line in f:
#             tno, tid, vol, maingas, microgas = line.split(",")
#             name = "kla t%s id%s" % (tno, tid)
#
#             if int(tid) == 26:
#                 continue
#
#             print(tno, tid, vol, maingas, microgas.rstrip("\n"))
#             r.create_test(float(maingas), float(microgas), float(vol), name)
#
#     try:
#         r.run_all()
#     finally:
#         return r
#
#
# def analyze_kla_from_file():
#     """
#     for MIC-TR-2-008
#     """
#     try:
#         from hello import kla
#     except ImportError:
#         import kla
#     import os
#
#     path = "C:\\.replcache\\kla12-07-15"
#     files = ["\\".join((path, f)) for f in os.listdir(path) if f.endswith(".csv")]
#     savepath = "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\kla id27 med membrane"
#     a = kla.KLAAnalyzer((), savepath, "kla id27 compiled")
#     for file in files:
#         name = os.path.split(file)[1]
#         name = os.path.splitext(name)[0]
#         a.add_file(file, name)
#     a.analyze_all()
#
#
# def kla_load_from_file2():
#     """
#     for MIC-TR-2-008
#     """
#     try:
#         from hello import kla
#     except ImportError:
#         import kla
#
#     rc = kla.KLAReactorContext(0.5, 0.5, 0.5, 0.3, 0.02, 0.5, 4, 1, 30, 30, 20)
#     tc = kla.KLATestContext(7, 5, 10)
#     r = kla.AirKLATestRunner("71.189.82.196:6", rc, tc)
#
#     name1 = "kla t15 id27"
#     r.create_test(0.153, 500, 3, name1)
#     name2 = "kla t16 id27"
#     r.create_test(0.459, 0, 3, name2)
#     name3 = "kla t17 id27"
#     r.create_test(0.459, 60, 3, name3)
#     r.run_all()


def kla_load_from_file3():
    """
    for MIC-TR-2-008
    """
    try:
        from hello import kla
    except ImportError:
        import kla

    rc = kla.KLAReactorContext(0.5, 0.5, 0.5, 0.3, 0.02, 0.5, 4, 1, 30, 30, 20)
    tc = kla.KLATestContext(7, 5, 10)
    r = kla.AirKLATestRunner("71.189.82.196:6", rc, tc)

    filepath = "C:\\Users\\PBS Biotech\\Downloads\\MIC-TR-X-008a.csv"
    with open(filepath, 'r') as f:
        f.readline()  # discard header

        for line in f:
            tno, tid, vol, maingas, microgas, run = line.split(",")
            name = "kla t%s id%s" % (tno, tid)

            if run.strip() != "x":
                continue

            print(tno, tid, vol, maingas, microgas)
            r.create_test(float(maingas), float(microgas), float(vol), name)
    try:
        r.run_all()
    finally:
        return r


def analyze_kla_from_file2():
    """
    for MIC-TR-2-008
    """
    try:
        from hello import kla, hello
    except ImportError:
        import kla, hello
    import os
    import pysrc.snippets

    path = "C:\\.replcache\\kla12-08-15"
    files2 = ["\\".join((path, f)) for f in os.listdir(path) if f.endswith(".csv")]
    savepath = "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\kla id27 med membrane"
    a = kla.KLAAnalyzer((), savepath, "kla id27 compiled")

    files = []
    for f in files2:
        if f.replace(".csv", "") + "(1).csv" in files2:
            continue
        else:
            files.append(f)
    # app = hello.HelloApp("71.189.82.196:6")
    # app.login()
    # # app.logout()
    # # app.login()
    # for t in (15,):
    #     name = "kla t%d id27" % t
    #     n = 0
    #     while True:
    #         n += 1
    #         try:
    #             b = app.getdatareport_bybatchname(name)
    #         except hello.TrueError:
    #             print("\r Trueerror #%d             " % n, end="")
    #             app.reconnect()
    #             app.login()
    #         else:
    #             break
    #     file = path + "\\" + name + ".csv"
    #     file = pysrc.snippets.unique_name(file)
    #     with open(file, 'wb') as f:
    #         f.write(b)
    #     a.add_file(file, name)

    for file in files:
        name = os.path.split(file)[1]
        name = os.path.splitext(name)[0]
        name = name.replace("(1)", "")
        a.add_file(file, name)
        print(name)
    a.analyze_all()


def analyze_kla_from_file3():
    """
    for MIC-TR-2-008
    """
    try:
        from hello import kla, hello
    except ImportError:
        import kla, hello
    import os

    savepath = "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\kla id27 small membrane"
    a = kla.KLAAnalyzer(None, savepath, "kla id27 compiled")

    path1 = "C:\\.replcache\\kla12-08-15"
    path2 = "C:\\.replcache\\kla12-09-15"

    testpath = "C:\\Users\\PBS Biotech\\Downloads\\MIC-TR-X-008a.csv"
    tests = {}
    with open(testpath, 'r') as f:
        f.readline()  # discard header

        for line in f:
            tno, tid, vol, maingas, microgas, run = line.split(",")
            name = "kla t%s id%s" % (tno, tid)
            tests[name] = "t%d %.3fLPM %dmLPM" % (int(tno), float(maingas), float(microgas))

    for path in (path1, path2):
        for file in os.listdir(path):
            if os.path.isdir(file):
                continue
            name = file.replace(".csv", "")
            a.add_file(os.path.join(path, file), tests[name])
            print(name)

    a.analyze_all()


def analyze_kla_from_file4():
    """
    for MIC-TR-2-008
    """
    try:
        from hello import kla, hello
    except ImportError:
        import kla
        import hello
    import os

    savepath = "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\kla id26 med membrane"
    a = kla.KLAAnalyzer(None, savepath, "kla id26 compiled")

    path1 = "C:\\.replcache\\kla12-11-15"
    # path2 = "C:\\.replcache\\kla12-14-15"

    testpath = "C:\\Users\\PBS Biotech\\Downloads\\MIC-TR-X-008a.csv"
    tests = {}
    with open(testpath, 'r') as f:
        f.readline()  # discard header

        for line in f:
            tno, tid, vol, maingas, microgas, run = line.split(",")
            name = "kla t%s id%s" % (tno, tid)
            tests[name] = "t%d %.3fLPM %dmLPM" % (int(tno), float(maingas), float(microgas))

    for path in (path1,):  # , path2):
        for file in os.listdir(path):
            if os.path.isdir(file):
                continue
            name = file.replace(".csv", "")
            a.add_file(os.path.join(path, file), tests[name])
            print(name)
    a.analyze_all()


if __name__ == '__main__':

    # kla_load_from_file()
    # analyze_kla_from_file2()
    # r = kla_load_from_file3()
    # analyze_kla_from_file3()
    analyze_kla_from_file4()
