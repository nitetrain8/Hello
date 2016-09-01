"""

Created by: Nathan Starkweather
Created on: 01/29/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from hello import HelloThing, HelloApp
from datetime import datetime
from time import sleep



class TempPoller(HelloThing):

    def __init__(self, ipv4, file):
        self.file = file
        HelloThing.__init__(self, ipv4)
        self.lines = []
        self.done = False

    def _poll_forever(self):
        app = self.app
        start = datetime.now()
        now = datetime.now
        self.write("Elapsed, TempPV, Temp SP, HeatDuty\n")

        while True:
            pv, sp = app.getautotempvals()
            hd = app.getadvv()['MainHeatDuty(%)']
            td = now() - start
            sec = td.total_seconds()
            self.write("%.1f, %.3f, %.3f, %.3f\n" % (sec, pv, sp, hd))
            sleep(10)

    def poll_forever(self):
        try:
            self._poll_forever()
        except KeyboardInterrupt:
            pass

    def write(self, line):
        self.lines.append(line)
        if line[-1] != "\n":
            self.lines.append("\n")
        print(line, end="", flush=True)

    def end(self):
        self.done = True
        with open(self.file, 'w') as f:
            f.writelines(self.lines)

    def __del__(self):
        if not self.done:
            self.end()


def main():
    fldr = "C:\\Users\\Public\\Documents\\PBSSS\\80L mech testing\\Temp PID"
    date = datetime.now().strftime("%y%m%d %H%M")
    path = "\\".join((fldr, "temp log %s.csv" % date))
    ipv4 = '192.168.1.4'
    app = HelloApp(ipv4)
    app.login()
    app.settemp(0, 39)
    p = TempPoller(app, path)
    try:
        print("Polling Forever")
        p.poll_forever()
    finally:
        p.end()
        app.login()
        app.settemp(0, 37)

if __name__ == '__main__':
    main()
