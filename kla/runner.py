"""

Created by: Nathan Starkweather
Created on: 02/03/2016
Created in: PyCharm Community Edition


"""
from datetime import datetime
from os import makedirs
from time import time as _time, sleep as _sleep
import traceback
from hello.hello import open_hello, HelloError, TrueError
from .exceptions import KLAError, SkipTest
from logger import BuiltinLogger
from snippets import safe_pickle, unique_name

__author__ = 'Nathan Starkweather'

_docroot = "C:\\.replcache\\"


class AirKLATestRunner():
    """
    Run a group of KLA tests on an air wheel reactor.
    """
    def __init__(self, ipv4, reactor_ctx=None, test_ctx=None):
        self.app = open_hello(ipv4)
        self.tests_to_run = []
        self.tests_run = []
        self.tests_skipped = []
        self.tests_pending = []
        self.ntests_run = 0

        self.logger = BuiltinLogger(self.__class__.__name__ + datetime.now().strftime("%m-%d-%Y %H-%M"))
        self.logger.handlers.pop(0)  # XXX bad practice

        if reactor_ctx is None:
            reactor_ctx = _default_r_ctx
        if test_ctx is None:
            test_ctx = _default_t_ctx

        self.reactor_ctx = reactor_ctx
        self.test_ctx = test_ctx

    def print(self, *args, **kwargs):
        print(*args, **kwargs)

        msg = kwargs.get("sep", " ").join(args).replace("\r", "")
        if msg:
            self.logger.info(msg)

    def import_batch(self, batchname):
        filename = self.test_ctx.generate_filename(batchname)
        t = AirKLATest(self.app, 0, 0, 0, batchname, self.reactor_ctx, self.test_ctx)

        r = _KLADataFile.from_download(batchname, filename, self.app.ipv4)
        t.report = r
        self.tests_run.append(t)

    def pickle_completed(self):
        pkl_file = self.test_ctx.savedir + "klapickle\\airklatestpikle.pkl"
        safe_pickle(self.tests_run, pkl_file)

    def add_test(self, test):
        """
        @type test: AirKLATest
        """
        test.print = self.print
        self.tests_to_run.append(test)

    def create_test(self, main_sp, micro_sp, volume, name):
        t = AirKLATest(self.app, main_sp, micro_sp, volume, name, self.reactor_ctx, self.test_ctx)
        self.add_test(t)
        return t

    def skip_current_test(self):
        t = self.tests_pending.pop()
        self.tests_skipped.append(t)

        self.app.login()
        if self.reactor_ctx.is_mag:
            self.app.setmg(2, 0)
        else:
            self.app.setag(2, 0)
        self.app.setph(2, 0, 0)
        self.app.setdo(2, 0, 0)
        self.app.logout()

    def run_once(self):
        self.ntests_run += 1
        t = self.tests_to_run.pop()
        self.print("-------------------------------------------")
        self.print("Test #%d starting: %s" % (self.ntests_run, t.get_info()))
        self.tests_pending.append(t)
        try:
            t.run()
        except SkipTest as e:
            self.print(e.args)
            self.skip_current_test()
        except Exception:
            traceback.print_exc()
            self.skip_current_test()
        else:
            self.tests_pending.pop()
            self.tests_run.append(t)
            assert t.report

    def run_all(self):
        # run all tests. reverse list in the beginning,
        # then run 1 by 1 using .pop() to iterate in
        # correct order while removing from list.
        self.tests_to_run.reverse()
        while self.tests_to_run:
            self.run_once()

        if self.tests_skipped:
            self.print("------------------------")
            self.print("Skipped tests:")
            for t in self.tests_skipped:
                self.print(t.get_info())


class AirKLATest():
    """
    Air KLA test.

    Requires hardware modification to configure tubing lines such that
    the test can be automated without requiring operator to switch tubing
    lines.

    Requirements for this class:
    * Air and N2 flow into main gas line
    * CO2 and O2 flow into micro gas line
    * Air and O2 flow compressed air
    * N2 and CO2 flow compressed nitrogen gas
    * PBS 2.0 software
    """

    def __init__(self, app, main_sp, micro_sp, volume, name,
                 reactor_ctx=None, test_ctx=None):
        """
        @param app: HelloApp
        @param main_sp: Main Gas (manual agitation) setpoint
        @param micro_sp: micro sparger (manual DO O2) setpoint
        @param volume: volume in reactor
        @param name: name to use for batch file.
        @param reactor_ctx: reactor context
        @type reactor_ctx: KLAReactorContext
        """
        self.name = name
        self.app = open_hello(app)
        self.main_sp = main_sp
        self.micro_sp = micro_sp
        self.volume = volume
        self.report = None

        if reactor_ctx is None:
            reactor_ctx = _default_r_ctx
        if test_ctx is None:
            test_ctx = _default_t_ctx

        if reactor_ctx.is_mag:
            self.set_gas = self.setmg
        else:
            self.set_gas = self.setag

        self.reactor_ctx = reactor_ctx
        self.test_ctx = test_ctx

        # Can be changed to logger.info, etc
        self.print = print

    def get_info(self):
        """
        @return: string describing the test
        """
        return '"%s" %.3fLPM %dmLPM %.2fL' % (self.name, self.main_sp, self.micro_sp, self.volume)

    __repr__ = get_info

    def run(self):

        self.print("Beginning setup")
        self.setup()

        self.print("Clearing headspace")
        self.clear_headspace()

        self.print("Running experiment")
        self.experiment()

        self.print("Post experiment cleanup")
        self.post_experiment()

        self.print("Experiment concluded")

    def _poll_do_setup(self, timeout):
        update_interval = 2
        end = timeout + _time()
        while True:
            do_pv = self.app.getdopv()
            if do_pv < self.test_ctx.do_start_target:
                return True
            if _time() > end:
                return False
            _sleep((end - _time()) % update_interval)
            self.print("\rDO PV: %.1f%% / %.1f%%                    " % (do_pv, self.test_ctx.do_start_target), end='')
        return True

    def _set_do_rampup(self):
        co2_flow = self.reactor_ctx.co2_min_flow
        n2_flow = co2_flow * 5
        total = co2_flow + n2_flow
        ph_pc = co2_flow / total * 100
        do_pc = n2_flow / total * 100
        self.app.setph(1, ph_pc, 0)
        self.app.setdo(1, do_pc, 0)
        self.set_gas(1, total)

    def _verify(self, used_ph_m, used_ph_sp,
                used_do_m, used_do_sp,
                used_gas_m, used_gas_sp):

        mv = self.app.gpmv()

        ph = mv['ph']
        ph_m = ph['mode']
        ph_sp = ph['manDown']

        do = mv['do']
        do_m = do['mode']
        do_sp = do['manUp']

        if self.reactor_ctx.is_mag:
            gas = mv['maingas']
        else:
            gas = mv['agitation']

        gas_m = gas['mode']
        gas_sp = gas['man']

        return all((ph_m == used_ph_m, ph_sp == used_ph_sp,
                    do_m == used_do_m, do_sp == used_do_sp,
                    gas_m == used_gas_m, gas_sp == used_gas_sp))

    def setup(self):
        """
        Lower DO to < 10% using N2 from CO2 (micro)
        and N2 (main) gas lines.

        loop for 30 minutes or until DO PV < 10%
        IP00044 Rev A calls for lowering DO PV to < 20%,
        but we lower to 10% because we will be using the
        main gas line to purge headspace gas.

        The extra 10% helps compensate for increase in
        DO PV caused by air bubbles passing through the
        solution during the headspace purge.

        The poll/wait loop is performed in `_poll_do_setup`.
        This makes it a lot easier to use as it needs to be
        used twice- once with low CO2 flow (to simulate the
        DO rampup feature) and once with max flow.
        """
        self.app.login()

        # fastpath
        if self.app.getdopv() > self.test_ctx.do_start_target:

            self.print("Beginning DO PV bringdown.")
            self._set_do_rampup()
            if not self._poll_do_setup(15):

                ph_pc = self.reactor_ctx.co2_mfc_max / self.reactor_ctx.main_gas_max * 100
                do_pc = 100 - ph_pc

                self.app.setph(1, ph_pc, 0)  # 3L -> 0.3 LPM CO2 micro sparger
                self.app.setdo(1, do_pc, 0)  # 3L -> 0.2 LPM N2 main sparger
                self.set_gas(1, self.reactor_ctx.main_gas_max)

                if not self._poll_do_setup(60 * 30):
                    self.print("")
                    raise SkipTest("Setup timeout waiting for DO PV < %d%%" % self.test_ctx.do_start_target)

                self.print("")

        # subtlety in this test setup- at this point, main and micro
        # gas lines are both full of nitrogen. The main gas line is
        # purged during headspace purge, but the N2 from micro
        # gas line will come out during experiment and cause problems.
        # so we have to clear that gas and then finish the bringdown with
        # main gas N2 only.
        self.app.login()
        o2_purge_time = self.reactor_ctx.o2_tubing_volume / self.reactor_ctx.o2_mfc_min
        self.app.setdo(1, 0, self.reactor_ctx.o2_mfc_min)
        self.print("Beginning micro gas line purge %d second sleep" % int(o2_purge_time * 60))
        self.app.logout()
        _sleep(o2_purge_time * 60)

        self.app.login()
        self.app.setdo(2, 0, 0)
        self.app.logout()
        self._poll_do_setup(60 * 10)

        # post setup- all controllers off.
        self.app.login()
        self.app.setph(2, 0, 0)
        self.app.setdo(2, 0, 0)
        self.set_gas(2, 0)

    def clear_headspace(self):
        """
        Run "headspace" gas to pass headspace volume * 5 L of air.
        """
        headspace = self.reactor_ctx.vessel_capacity - self.volume
        t_min = headspace / self.reactor_ctx.main_gas_max * self.test_ctx.hs_purge_factor

        self.app.login()
        self.app.setph(2, 0, 0)
        self.app.setdo(2, 0, 0)
        self.set_gas(1, self.reactor_ctx.main_gas_max)

        now = _time()
        end = now + 60 * t_min
        while True:
            left = end - _time()
            left = max(left, 0)
            if left < 15:
                if left:
                    self.print("\r                                          ", end="")
                    self.print("\rHeadspace purge: %s seconds remain" % (int(end - _time())), end="")
                    _sleep(left)
                break
            else:
                _sleep(int(left) % 15)
                self.print("\r                                          ", end="")
                self.print("\rHeadspace purge: %s seconds remain" % (int(end - _time())), end="")
                _sleep(1)

        self.print("\nPurge Finished")
        self.app.login()
        self.set_gas(2, 0)

    def _begin_batch(self, max_tries=20):
        """
        Subroutine to ensure that batch is started
        some issues have arisen with server calls
        not being accepted.

        Issue #1: startbatch not accepted.
        Issue #2: ODBC database driver error or w/e
        """
        n = 1
        while True:
            self.print("\rAttempting to begin batch: Attempt #%d of %d              "
                       % (n, max_tries))
            try:
                self.app.startbatch(self.name)
            except HelloError:  # odbc error
                pass
            _sleep(1)
            bn = self.app.getDORAValues()['Batch']
            if bn.lower() == self.name.lower():
                return
            if n > max_tries:
                raise SkipTest("Failed to start batch")
            n += 1

    def experiment(self):

        self.app.login()

        if self.app.batchrunning():
            self.app.endbatch()

        self.app.setph(2, 0, 0)
        self.app.setdo(1, 0, self.micro_sp)
        self.set_gas(1, self.main_sp)

        self.print("Sleeping %d seconds for O2 rampup" % self.reactor_ctx.o2_min_flow_time)
        _sleep(self.reactor_ctx.o2_min_flow_time)

        self._begin_batch()
        self.app.logout()

        end = _time() + self.test_ctx.test_time * 60
        update_interval = 5
        dopv = 0.0
        while True:
            left = max(end - _time(), 0)
            if left < update_interval:
                _sleep(left)
                assert _time() >= end
                break
            self.print("\r                                                          ", end="")
            try:
                dopv = self.app.getdopv()
            except:
                pass
            self.print("\rExperiment running: %s seconds left. DO PV: %.1f%%" %
                       (int(end - _time() + 1), dopv), end="")
            _sleep(left % update_interval)

        self.print("")
        self.app.login()

        self.set_gas(2, 0)
        self.app.setdo(2, 0)
        self.app.endbatch()

    def _try_getreport(self, n, max_tries=20):
        batch = None  # pycharm
        while True:
            self.app.login()
            self.print("\rAttempting to download report: Attempt #%d of %d              "
                       % (n, max_tries))
            try:
                batch = self.app.getdatareport_bybatchname(self.name)
            except TrueError:
                if n > max_tries:
                    raise
                try:
                    self.app.logout()
                except HelloError:
                    pass
                self.app.reconnect()
                n += 1
            else:
                break
        return batch

    def post_experiment(self):
        filename = self.test_ctx.generate_filename(self.name)
        self.report = _KLADataFile.from_download(self.name, filename, self.app.ipv4)

    def setmg(self, mode, val):
        self.app.setmg(mode, val)

    def setag(self, mode, val):
        self.app.setag(mode, val)


class KLATestContext():
    """
    Test parameters for the test itself.
    Includes filename info, etc.
    """
    def __init__(self, test_time, headspace_purge_factor, do_start_target, savedir=_docroot):
        self.test_time = test_time
        self.hs_purge_factor = headspace_purge_factor
        self.do_start_target = do_start_target
        self.savedir = savedir

    def generate_filename(self, name):
        """
        Generate filename.
        Default impl based on current date.
        Override for custom behavior if desired.
        """
        dirname = "%s%s%s\\" % (self.savedir, "kla",
                                datetime.now().strftime("%m-%d-%y"))
        makedirs(dirname, exist_ok=True)
        filename = dirname + name + ".csv"
        filename = unique_name(filename)
        return filename

    def __repr__(self):
        return "KLATestContext: %d min test time, %dx headspace purge, %d%% DO start target" % \
               (self.test_time, self.hs_purge_factor, self.do_start_target)


class KLAReactorContext():
    def __init__(self, air_mfc_max, n2_mfc_max, o2_mfc_max,
                 co2_mfc_max, co2_min_flow, main_gas_max, vessel_capacity, is_mag, o2_min_flow_time,
                 o2_tubing_volume, o2_mfc_min):
        """

        @param air_mfc_max: air mfc max in L/min
        @param n2_mfc_max: n2 mfc max in L/min
        @param o2_mfc_max: o2 mfc max in L/min
        @param co2_mfc_max: co2 mfc max in L/min
        @param co2_min_flow: co2 mfc min in L/min
        @param main_gas_max: main gas manual max (highest of above values)
        @param vessel_capacity: total capacity of vessel (eg, 4L for 3L, 100L for 80L...)
        @param is_mag: 1 if doing air test on mag drive unit, 0 if air on air drive.
        @param o2_min_flow_time: time to wait for o2 to ramp up, in seconds

        POD class: parameters for reactor configuration
        """
        self.air_mfc_max = air_mfc_max
        self.n2_mfc_max = n2_mfc_max
        self.o2_mfc_max = o2_mfc_max
        self.co2_mfc_max = co2_mfc_max
        self.co2_min_flow = co2_min_flow
        self.main_gas_max = main_gas_max
        self.vessel_capacity = vessel_capacity
        self.is_mag = is_mag
        self.o2_min_flow_time = o2_min_flow_time
        self.o2_tubing_volume = o2_tubing_volume
        self.o2_mfc_min = o2_mfc_min

    def __repr__(self):
        return "KLAReactorContext: %.1f LPM Air MFC, %.1f LPM N2 MFC, %.1f LPM CO2 MFC, %.1f LPM O2 MFC," \
               "%.1f LPM main gas max, %dL total vessel capacity, %s Drive" % \
               (self.air_mfc_max, self.n2_mfc_max,
               self.co2_mfc_max, self.o2_mfc_max,
               self.main_gas_max, self.vessel_capacity,
               "Mag" if self.is_mag else "Air")

pbs_3L_ctx = KLAReactorContext(0.5, 0.5, 0.5, 0.3, 0.02, 0.5, 4, 1, 30, 30, 20)
_default_r_ctx = pbs_3L_ctx
_default_t_ctx = KLATestContext(7, 5, 10)


class MechKLATest():
    """ KLA test runner designed ground-up to work for
    *3L Mag Wheel* only! If using any other setup, review code to verify
     it will work correctly!!!

     Since mag drive uses headspace to "sparge" the vessel with oxygen,
     no operator activity with tubing, gases, etc is necessary in certain
     circumstances.

     This class ASSUMES THE FOLLOWING:

     * 1.3 hello software
     * Logger settings are correct
     * N2 gas is connected to a tank with sufficient volume, to N2 AND O2 inlets
     * Air is connected to a compressor (or tank w/ sufficient volume) to air inlet
     * Vessel is inserted in reactor, with Main and Micro gas lines connected
     * All ports on the top of the vessel are closed
     * Filter oven is only open line for gas to escape
     * Vessel has Main Gas connector on L-plate snipped.
     * Vessel has Micro Gas connector on L-plate intact!
    """
    def __init__(self, ipv4, vessel_max=4, max_mfc_rate=0.5, setup_timeout=None):
        self.logger = BuiltinLogger("MechKLATest")
        self._max_mfc_rate = max_mfc_rate
        self._vessel_max = vessel_max
        self._setup_timeout = setup_timeout or (2 ** 31 - 1)
        self.app = open_hello(ipv4)
        self._reports = None

    def setup(self):

        self.logger.info("Initializing KLA Setup")

        app = self.app
        app.login()
        app.setag(1, 50)
        app.setdo(1, 0, 500)

        start = _time()

        self.logger.info("Begin setup. Waiting for DO < 20%")
        log_time = _time() + 10
        while app.getdopv() > 20:
            t = _time()
            if t > log_time:
                log_time = int(t) + 10
                self.logger.info("Waiting for DO to fall below 20.")
                self.logger.info("%d seconds: %.1f%% DO" % (t - start, app.getdopv()))
            _sleep(1)

        app.setdo(2, 0, 0)
        app.setmg(2, 0)

    def clear_headspace(self, media_volume):

        self.logger.info("Preparing to purge headspace")

        # math
        headspace = self._vessel_max - media_volume
        sleep_time = headspace / self._max_mfc_rate * 60

        app = self.app
        app.login()
        app.setdo(2, 0)
        app.setmg(1, self._max_mfc_rate)

        self.logger.info("Purging headspace at %.3f LPM for %d seconds" % (self._max_mfc_rate, sleep_time))

        time = _time
        sleep = _sleep
        t = time()
        end = t + sleep_time
        log_time = int(t) + 10

        while t < end:
            if t > log_time:
                log_time = int(t) + 10
                left = int(end - t)
                self.logger.info("Purging headspace. %s seconds remaining" % left)
            t = time()
            sleep(5)

        # login again in case sleep_time was long
        app.login()
        app.setmg(2, 0)

    def run(self, volume, experiments):
        # batches is list of batch names
        batches = self.run_experiments(volume, experiments)

        if self._reports is None:
            reports = self._reports = []
        else:
            reports = self._reports

        batch_list = self.app.getBatches()

        for name in batches:
            id = batch_list.getbatchid(name)
            r = self.app.getdatareport_bybatchid(id)
            b = _KLADataFile(name, id, r)
            reports.append(b)
        return reports

    def run_experiments(self, volume, experiments):
        """
        @param volume: volume of media in L
        @param experiments: 3 tuple (ag_mode, ag_sp, flow_rate)
        @type experiments: ((int | float, int | float, int | float)) | list[(int | float, int | float, int | float)]
        @return: list of batches
        @rtype: list[str]
        """
        batches = []

        self.logger.info("Running %d experiments." % len(experiments))
        for i, (mode, sp, flowrate) in enumerate(experiments, 1):

            self.logger.info("Running test %d of %d" % (i, len(experiments)))

            try:
                self.setup()
            except KeyboardInterrupt:
                self.logger.error("Got keyboard interrupt, skipping setup.")

            try:
                self.clear_headspace(volume)
            except KeyboardInterrupt:
                self.logger.error("Got keyboard interrupt, skipping headspace purge.")

            try:
                b = self.experiment(mode, sp, flowrate, volume)
                batches.append(b)
            except KeyboardInterrupt:
                self.logger.error("Got keyboard interrupt, skipping test.")
                continue
            finally:
                mv = self.app.gpmv()
                if mv['do']['mode'] != 2:
                    while True:
                        try:
                            self.app.login()
                            self.app.setdo(2, 0, 0)
                            break
                        except Exception:
                            self.logger.error("Error shutting down test.")
                            self.app.reconnect()

        return batches

    def experiment(self, ag_mode, ag_sp, flow_rate, volume):
        """
        @param flow_rate: flow rate in *mL per min*
        """
        app = self.app
        app.login()
        time = _time

        self.logger.info("Initializing Agitation with mode=%s sp=%s." % (ag_mode, ag_sp))
        app.setag(ag_mode, ag_sp)

        # if setpoint is auto mode, wait for pv to reach correct value
        if ag_mode == 0:
            timeout = time() + 10 * 60
            log_time = time() + 10
            while True:
                pv = app.getagpv()
                if ag_sp - 1 < pv < ag_sp + 1:
                    break
                t = time()
                if t > log_time:
                    log_time = int(t) + 10
                    self.logger.info("Waiting for Agitation to reach setpoint. PV = %d." % app.getagpv())
                if t > timeout:
                    raise KLAError("Agitation didn't reach setpoint.")
                _sleep(1)

        app.setmg(1, flow_rate / 1000)

        self.logger.info("Beginning KLA Experiment.")

        batch_name = "kla%s-%s-%s-%s" % (ag_mode, volume, ag_sp, flow_rate)

        self.logger.info("Starting new batch named '%s'." % batch_name)
        if app.batchrunning():
            app.endbatch()
        app.startbatch(batch_name)

        start = time()
        end = start + 14 * 60
        log_time = start + 10
        while True:
            t = time()
            pv = app.getdopv()
            if t > log_time:
                self.logger.info("Test running, %d seconds passed. DO PV = %.1f." % (t - start, pv))
                log_time += 10
            if t > end:
                break
            if pv > 90:
                break

        self.logger.info("Test finished. DO PV = %.1f after %d seconds." % (app.getdopv(), time() - start))

        self.logger.info("Ending batch")
        app.endbatch()
        return batch_name



