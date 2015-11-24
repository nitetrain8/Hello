"""

Created by: Nathan Starkweather
Created on: 03/03/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'
from os import listdir
from os.path import join as _path_join, split as _path_split
from officelib.xllib import xlcom, xladdress
from officelib import const
from hello.logger import BuiltinLogger


class TorqueTest():
    def __init__(self, size, wt, startx, starty, endy):
        self.size = size
        self.wt = wt
        self.name = "%s %s" % (size, wt)
        self.startx = startx
        self.starty = starty
        self.endy = endy


class TorqueAnalyzer():

    HEADER_ROW = 1
    LABEL_ROW = 2
    DATA_ROW = 3
    XAXIS_NAME = "time(s)"
    YAXIS_NAME = "RPM"
    CHART_MARKERSIZE = 5

    def __init__(self):
        self.column = 1
        self.xl, self.wb, self.ws, self.cells = xlcom.xlObjs(new=True)
        self.ws.Name = "Raw"
        self.sizes = {}
        self.weights = {}
        self.tests = []
        self.logger = BuiltinLogger(self.__class__.__name__)

    def add_file(self, file_path):
        self.logger.info("Adding file: %s" % file_path)
        _, file = _path_split(file_path)
        name = file.rsplit(".", 1)[0]
        size, wt = name.split(" ")
        self.logger.debug("Opening file for reading")
        with open(file_path, 'r') as f:
            f.readline()  # header
            contents = f.read()
        self.logger.debug("Successfully read file, parsing...")
        contents = [line.split("\t") for line in contents.splitlines()]
        self._add_data_set(size, wt, contents)

    @classmethod
    def from_dir(cls, path):
        self = cls()
        self.logger.info("Opening all files in path: %s" % path)
        for file in listdir(path):
            file_path = _path_join(path, file)
            self.add_file(file_path)

        return self

    def _register_test(self, t):
        self.logger.debug("Registering test: size %s, wt %s" % (t.size, t.wt))
        if t.size not in self.sizes:
            self.sizes[t.size] = {}
        if t.wt not in self.weights:
            self.weights[t.wt] = {}

        self.sizes[t.size][t.name] = t
        self.weights[t.wt][t.name] = t
        self.tests.append(t)

    def _add_data_set(self, size, wt, contents):
        self.logger.debug("Inner add file: %s %s" % (size, wt))
        cells = self.cells
        header = [(size, "%s %s" % (size, wt), wt)]
        labels = [("ticks", "time(s)", "RPM")]
        # self.logger.debug("Header: %s" % header)
        # self.logger.debug("Labels: %s" % labels)
        cells.Range(cells(self.HEADER_ROW, self.column), cells(self.HEADER_ROW, self.column + 2)).Value = header
        cells.Range(cells(self.LABEL_ROW, self.column), cells(self.LABEL_ROW, self.column + 2)).Value = labels

        nrows = len(contents)
        endrow = self.DATA_ROW + nrows - 1

        self.logger.debug("Data Coords: x1 %s, y1 %s, x2 %s, y2 %s" %
                          (self.DATA_ROW, self.column, endrow, self.column + 1))
        cells.Range(cells(self.DATA_ROW, self.column), cells(endrow, self.column + 1)).Value = contents

        t = TorqueTest(size, wt, self.column, self.DATA_ROW, endrow)
        self._register_test(t)

        self.column += 4

    def plot_by_size(self):
        # todo debug logging
        # todo add trendlines
        self.logger.info("Plotting by Size")
        for size, tests in self.sizes.items():
            chart = xlcom.CreateChart(self.ws)
            xlcom.FormatChart(chart, None, size, self.XAXIS_NAME, self.YAXIS_NAME, True)
            for name, test in tests.items():
                xrng, yrng = xladdress.chart_range_strs(test.startx, test.startx + 1, test.starty, test.endy, self.ws.Name)
                series = xlcom.CreateDataSeries(chart, xrng, yrng, test.name)
                series.MarkerSize = self.CHART_MARKERSIZE
            chart.Location(const.xlLocationAsNewSheet, "%s Chart" % size)

    def plot_by_weight(self):
        # todo debug logging
        # todo add trendlines
        self.logger.info("Plotting by Weight")
        for wt, tests in self.weights.items():
            chart = xlcom.CreateChart(self.ws)
            xlcom.FormatChart(chart, None, wt, self.XAXIS_NAME, self.YAXIS_NAME, True)
            for name, test in tests.items():
                xrng, yrng = xladdress.chart_range_strs(test.startx, test.startx + 1, test.starty, test.endy,
                                                        self.ws.Name)
                series = xlcom.CreateDataSeries(chart, xrng, yrng, test.name)
                series.MarkerSize = self.CHART_MARKERSIZE
            chart.Location(const.xlLocationAsNewSheet, "%s Chart" % wt)

    def plot_all(self):
        with xlcom.HiddenXl(self.xl):
            self.plot_by_size()
            self.plot_by_weight()


def main_150303():
    path = "C:\\Users\\PBS Biotech\\New folder\\Dropbox\\Nathan's Stuff\\mini torque data\\mini\\initial raw data"
    analyzer = TorqueAnalyzer.from_dir(path)
    analyzer.plot_by_size()
    analyzer.plot_by_weight()

if __name__ == '__main__':
    main_150303()
