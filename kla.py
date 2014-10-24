"""

Created by: Nathan Starkweather
Created on: 10/21/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'


from hello import Logger, HelloThing, HelloError, HelloApp
from time import time as _time, sleep as _sleep


class KLAError(HelloError):
    pass


class KLATest(Logger, HelloThing):
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
    def __init__(self, app_or_ipv4, vessel_max=4, max_mfc_rate=0.5, setup_timeout=None):
        Logger.__init__(self, "KLATest")
        HelloThing.__init__(self, app_or_ipv4)
        self._max_mfc_rate = max_mfc_rate
        self._vessel_max = vessel_max
        self._setup_timeout = setup_timeout or (2**31 - 1)
        self._init_app()

        # temp hack to solve connection issues 10/22/14
        import types
        klatest = self

        def reconnect(self):
            klatest._log("Connection reconnecting")
            self.reconnect()
            self.login()
        self._app.reconnect = types.MethodType(reconnect, self._app)

    def setup(self):

        self._log("Initializing KLA Setup")
        app = self._app
        app.login()
        app.setag(1, 50)
        app.setdo(1, 0, 500)
        # app.setdo(1, 100, 500)
        # app.setmg(1, 0.5)

        start = _time()
        timeout = start + self._setup_timeout

        # self._log("Beginning setup with timeout of %d seconds" % self._setup_timeout)

        log_time = _time() + 10
        while app.getdopv() > 20:
            t = _time()
            if t > log_time:
                self._log("Waiting for DO to fall below 20.")
                self._log("%d seconds: %.1f%% DO" % (t - start, app.getdopv()))
                log_time = t + 10
            # if t > timeout:
            #     raise KLAError("Test Timed out")
            _sleep(1)

        app.setdo(2, 0, 0)
        app.setmg(2, 0)

    def clear_headspace(self, media_volume):

        self._log("Preparing to purge headspace")

        # math
        headspace = self._vessel_max - media_volume
        sleep_time = headspace / self._max_mfc_rate * 60

        app = self._app
        app.login()
        app.setdo(2, 0)
        app.setmg(1, self._max_mfc_rate)

        self._log("Purging headspace at %.3f LPM for %d seconds" % (self._max_mfc_rate, sleep_time))
        _sleep(sleep_time)

        # login again in case sleep_time was long
        app.login()
        app.setmg(2, 0)

    def run_experiments(self, volume, experiments):
        """
        @param volume: volume of media in L
        @param experiments: 3 tuple (ag_mode, ag_sp, flow_rate)
        @type experiments: ((int | float, int | float, int | float)) | list[(int | float, int | float, int | float)]
        @return:
        """
        batches = []
        for mode, sp, flowrate in experiments:
            try:
                self.setup()
            except KeyboardInterrupt:
                self._log_err("Got keyboard interrupt, skipping setup")
            try:
                self.clear_headspace(volume)
            except KeyboardInterrupt:
                self._log_err("Got keyboard interrupt, skipping headspace purge")
            try:
                b = self.experiment(mode, sp, flowrate)
                batches.append(b)
            except KeyboardInterrupt:
                self._log_err("Got keyboard interrupt, skipping test")
            finally:
                mv = self._app.gpmv()
                if mv['do']['mode'] != 2:
                    while True:
                        try:
                            self._app.login()
                            self._app.setdo(2, 0, 0)
                            break
                        except Exception:
                            self._log_err("Error shutting down test")
                            self._app.reconnect()

        return batches

    def experiment(self, ag_mode, ag_sp, flow_rate):
        """
        @param flow_rate: flow rate in *mL per min*
        """
        app = self._app
        app.login()

        self._log("Initializing Agitation with mode=%s sp=%s" % (ag_mode, ag_sp))
        app.setag(ag_mode, ag_sp)

        # if setpoint is auto mode, wait for pv to reach correct value
        if ag_mode == 0:
            timeout = 10 * 60
            end = _time() + timeout
            log_time = _time() + 10
            while True:
                pv = app.getagpv()
                if ag_sp - 1 < pv < ag_sp + 1:
                    break
                t = _time()
                if t > log_time:
                    self._log("Waiting for Agitation to reach setpoint. PV = %d" % app.getagpv())
                    log_time = t + 10
                _sleep(1)
                if t > end:
                    raise KLAError("Agitation didn't reach setpoint")

        app.setmg(1, flow_rate / 1000)

        time = _time

        start = time()
        timeout = start + 14 * 60

        self._log("Beginning KLA Experiment")

        batch_name = "KLA%s-%s-%s" % (ag_mode, ag_sp, flow_rate)

        self._log("Starting new batch named '%s'" % batch_name)
        if app.batchrunning():
            app.endbatch()
        app.startbatch(batch_name)

        log_time = time() + 10
        while True:
            t = time()
            pv = app.getdopv()
            if t > log_time:
                self._log("Test running for %d seconds. DO PV = %.1f" % (t, pv))
                log_time = t + 10
            if t > timeout:
                break
            if pv > 90:
                break

        self._log("Test finished. DO PV = %.1f after %d seconds" % (app.getdopv(), time() - start))

        self._log("Ending batch")
        app.endbatch()
        return batch_name


if __name__ == '__main__':
    test = KLATest('192.168.1.6')
    test.setup()
