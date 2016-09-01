"""

Created by: Nathan Starkweather
Created on: 10/21/2014
Created in: PyCharm Community Edition


"""

from .analyzer import KLAAnalyzer, KLAReportFile
from .runner import KLATestContext, KLAReactorContext, KLAError, AirKLATestRunner, AirKLATest, MechKLATest, \
    pbs_3L_ctx
from .exceptions import KLAError


__author__ = 'Nathan Starkweather'

try:
    from hello import HelloError, HelloApp, open_hello, TrueError
except ImportError:
    from hello.hello import HelloError, HelloApp, open_hello, TrueError


# class _dbgmeta(type):
#     level = 0
#
#     def __new__(mcs, name, bases, kwargs):
#         from types import FunctionType
#
#         def decorator(f):
#             def wrapper(*args, **kwargs):
#                 nonlocal mcs
#                 print(mcs.level * " ", "Function called: ", f.__name__, sep='')
#                 mcs.level += 1
#                 rv = f(*args, **kwargs)
#                 mcs.level -= 1
#                 print(mcs.level * " ", "Function returned: ", f.__name__, sep='')
#                 return rv
#             return wrapper
#
#         for k, v in kwargs.items():
#             if isinstance(v, FunctionType):
#                 kwargs[k] = decorator(v)
#
#         # fuck it
#         for k, v in globals().items():
#             if isinstance(v, FunctionType):
#                 globals()[k] = decorator(v)
#
#         return type.__new__(mcs, name, bases, kwargs)


def __test_analyze_kla():

    import subprocess
    subprocess.call("tskill.exe excel")
    test_dir = "C:\\Users\\Public\\Documents\\PBSSS\\KLA Testing\\PBS 3 mech wheel\\test\\"
    file = test_dir + "kla0-10-200 id-35 27-10-14.csv"
    test_save_dir = "C:\\.replcache\\__test_analyze_kla\\"

    import shutil
    shutil.rmtree(test_save_dir)

    KLAAnalyzer((file,), test_save_dir).analyze_all()


def __test_airkla():
    from .runner import AirKLATestRunner
    rc = KLAReactorContext(0.5, 0.5, 0.5, 0.3, 0.02, 0.5, 4, 1, 30, 30, 20)
    tc = KLATestContext(7, 5, 5)

    r = AirKLATestRunner("71.189.82.196:6", rc, tc)
    r.test_ctx.hs_purge_factor = 0.5
    r.test_ctx.test_time = 1
    r.test_ctx.do_start_target = 15

    r.create_test(0.051, 60, 3, "kla t11 id27")
    r.create_test(0.153, 60, 3, "kla t55 id55")
    return r


if __name__ == '__main__':
    # test = MechKLATest('192.168.1.6')
    # test.setup()
    # r = __test_airkla()
    # t = r.tests_to_run[0]
    # t.setup()
    __test_analyze_kla()
    # pass

