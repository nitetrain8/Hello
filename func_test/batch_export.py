"""

Created by: Nathan Starkweather
Created on: 08/21/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from hello.hello import HelloApp
import os
import officelib.const
from officelib.xllib import xlcom, xladdress


_func_test_folder = "\\\\PBSStation\\PBSCloudShare\\(4) Manufacturing & Operations\\Functional Testing"
_backup_folder = os.path.join(os.path.abspath(os.path.expanduser("~")), "Documents", "PBS", "Local Functional Testing")

class BatchExporter():
    def __init__(self, ipv4, reactor_name, rsize):
        self.ipv4 = ipv4
        self.reactor_name = reactor_name
        self.rsize = rsize
        if ipv4:
            print("Connecting to ", ipv4, "...")
            self.app = HelloApp(ipv4)
        else:
            self.app = None

    def _temp_unique_name(self, batch_name):
        i = ""
        n = 0
        fname = ""
        if os.path.exists(_func_test_folder):
            folder = _func_test_folder
        else:
            folder = _backup_folder
        path = os.path.join(folder, self.rsize, self.reactor_name)
        os.makedirs(path, exist_ok=True)
        while True:
            fname = os.path.join(path, "%s%s%s" % (batch_name, i, ".csv"))
            if not os.path.exists(fname):
                break
            n += 1
            i = " %d" % n
        return path, fname

    def _save_temp(self, batch_name, report):

        path, fname = self._temp_unique_name(batch_name)
        if not os.path.exists(path):
            os.makedirs(path)
        with open(fname, 'wb') as f:
            f.write(report)
        return fname
        
    def analyze(self, batch_name, report):
        tmp = self._save_temp(batch_name, report)
        self._do_xl_import(tmp)

    def export(self, batch_name):
        if not self.app:
            raise ValueError("Error- no app!")
        self.app.login('pbstech', '727246')
        if self.app.batchrunning():
            print("Stopping running batch...")
            self.app.endbatch()
        print("Downloading File...")
        report = self.app.getdatareport_bybatchname(batch_name)
        print("Analyzing File...")
        self.analyze(batch_name, report)

    def _do_xl_import(self, tmpname):
        xl, wb, ws, cells = xlcom.xlObjs(tmpname, visible=False)
        with xlcom.HiddenXl(xl):
            xrng, yrng = xladdress.column_pair_range_str_by_header(cells, 'LevelPV(L)')
            chart = xlcom.CreateChart(ws)
            chart_name = "%s Batch Export" % self.reactor_name
            xlcom.CreateDataSeries(chart, xrng, yrng)
            xlcom.FormatChart(chart, None, chart_name, "Date", "LevelPV", Legend=False)
            chart.Location(officelib.const.xlLocationAsNewSheet)


def main(ipv4, reactor_name, rsize, batch_name='test1'):

    print("Beginning export...")
    try:
        BatchExporter(ipv4, reactor_name, rsize).export(batch_name)
    except:
        print("Error")
        raise
    else:
        print("Export Successful")
        
def main2(ipv4, reactor_name, rsize, filename, batch_name='test1'):
    print("Beginning export...")
    try:
        b = BatchExporter(ipv4, reactor_name, rsize)
        with open(filename, 'rb') as f:
            report = f.read()
        b.analyze(batch_name, report)
    except:
        print("Error")
        raise
    else:
        print("Export Successful")


def test():
    main("192.168.1.124", "PBS 3 Demo XIX", "3L")

def outer_main():
        # test()
    ipv4 = input("Enter IPV4, or 'none' to search for local file: ")
    if not ipv4 or ipv4.lower() == 'none':
        ipv4 = None
        print("No ipv4 given, browse for local file")
        from tkinter.filedialog import askopenfilename
        fn = askopenfilename(initialdir=_func_test_folder)
        if not fn:
            print("Aborting")
            import sys
            sys.exit(-1) 
            
    reactor_name = input("Enter reactor name: ")
    rsize = input("Enter reactor size: ")
    batch_name = input("Enter Batch Name: ")
    batch_name = batch_name or "test1"
   
    if ipv4 is None:
        main2(ipv4, reactor_name, rsize, fn, batch_name)
    else:
        main(ipv4, reactor_name, rsize, batch_name)

if __name__ == '__main__':
    try:
        outer_main()
    except:
        import traceback
        traceback.print_exc()
        
    input("Press Enter to Exit")
