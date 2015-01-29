"""

Created by: Nathan Starkweather
Created on: 01/23/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'


from officelib.xllib import xlcom, xladdress
from officelib import const


debug = 1
if debug:
    dprint = print
else:
    dprint = lambda *_, **__: None


def set_axis_name(axis, name):
    axis.HasTitle = True
    axis.AxisTitle.Text = name


def main(file_name):
    xl, wb, ws, cells = xlcom.xlObjs(file_name)
    with xlcom.HiddenXl(xl):
        analyze(xl, wb, ws, cells, file_name)


def autofit_columns(ws):
    i = 1
    cols = ws.Columns
    while True:
        c = cols(i)
        if not c.Cells(1, 1).Text:
            break
        c.AutoFit()
        i += 3


def save_from_file_name(file_name):
    save_name = ''.join(file_name.split(".")[:-1])
    save_name += ".xlsx"
    return save_name


def set_axis_titles(chart, xtitle, y1title, y2title=None):
    # axes (type, group) - type 1 = xaxis - type 2 = yaxis (?)
    # group = axisgroup
    axes = chart.Axes
    xaxis = axes(1, 1)
    y1axis = axes(2, 1)
    set_axis_name(xaxis, xtitle)
    set_axis_name(y1axis, y1title)

    if y2title is not None:
        y2axis = axes(2, 2)
        set_axis_name(y2axis, y2title)


def move_chart(chart, sheet_name):
    chart.Location(const.xlLocationAsNewSheet, sheet_name)


def add_ph_do_chart(cells, ws):

    chart = xlcom.CreateChart(ws)

    chart_title = "Headspace Tuning pH & DO Data"
    x_axis_title = "Time"
    xlcom.FormatChart(chart, None, chart_title, x_axis_title)

    ph_name = "pHPV"
    do_name = "DOPV(%)"

    add_to_chart_from_header(chart, cells, ph_name)
    add_to_chart_from_header(chart, cells, do_name, 2)
    set_axis_titles(chart, x_axis_title, ph_name, do_name)

    sheet_name = "pH DO data"
    move_chart(chart, sheet_name)
    return chart


def analyze(xl, wb, ws, cells, file_name, autosave=1):

    dprint("Analyzing file:", file_name)
    autofit_columns(ws)

    add_ph_do_chart(cells, ws)
    add_gases_chart(cells, ws)
    add_request_chart(cells, ws)

    if autosave:
        save_name = save_from_file_name(file_name)
        wb.SaveAs(save_name)
        dprint("Saving as", save_name)
    else:
        dprint("File analyzed but not saved!")


def add_gases_chart(cells, ws):

    chart = xlcom.CreateChart(ws)

    chart_title = "Headspace Tuning Gas Flow Feedback"
    x_axis_title = "Time"
    xlcom.FormatChart(chart, None, chart_title, x_axis_title)

    gas_names = ["MFC%sFlowFeedback(LPM)" % g for g in ("CO2", "O2", "N2", "Air")]

    for g in gas_names:
        add_to_chart_from_header(chart, cells, g)

    set_axis_titles(chart, "Time", "Flow (LPM)")
    move_chart(chart, "Feedback")

    return chart


def add_request_chart(cells, ws):

    chart = xlcom.CreateChart(ws)
    chart_title = "Headspace Tuning Gas Request"
    x_axis_title = "Time"
    xlcom.FormatChart(chart, None, chart_title, x_axis_title)

    add_to_chart_from_header(chart, cells, "pHCO2ActualRequest(%)")
    add_to_chart_from_header(chart, cells, "DON2FlowActualRequest(%)")

    set_axis_titles(chart, "Time", "Gas Request (%)")
    move_chart(chart, "Gas Request")


def copy_to_data_sheet(cells, header):
    wb = cells.Parent.Parent
    try:
        data = wb.Worksheets("Data")
    except xlcom.py_com_error:
        data = wb.Worksheets.Add()
        data.Name = "Data"

    datacells = data.Cells
    ncols = data.UsedRange.Columns.Count
    datacol = ncols + 2
    if ncols == 1:
        datacol = 1

    cell = cells.Find(What=header, After=cells(1, 1), SearchOrder=const.xlByRows)
    fromcol = cell.Column
    fromrow = cell.Row
    endfromrow = cell.End(const.xlDown).Row

    fromrng = cells.Range(cells(fromrow, fromcol), cells(endfromrow, fromcol + 1))
    datarng = datacells.Range(datacells(1, datacol), datacells(endfromrow - fromrow + 1, datacol + 1))

    datarng.Value = fromrng.Value

    return datacells


def add_to_chart_from_header(chart, cells, header, axisgroup=1, markersize=2):
    """
    @param chart: chart. Pass "None" to create a new chart
    @param cells: cells
    @param header: string to search for
    @return:
    """
    # datacells = copy_to_data_sheet(cells, header)
    x, y = xladdress.column_pair_range_str_by_header(cells, header)
    series = xlcom.CreateDataSeries(chart, x, y, header)
    series.AxisGroup = axisgroup
    series.MarkerSize = markersize
    return series

# repl
atcfh = add_to_chart_from_header


def test():
    file = "C:\\Users\\Public\\Documents\\PBSSS\\80L mech testing\\" \
           "Headspace gas PID tuning\\pbs 80 mag 1 headspacetest001 #2.csv"

    main(file)


def download_batches_150128(do_download=False):
    import os

    pth = "C:\\Users\\Public\\Documents\\PBSSS\\80L mech testing\\" \
          "Headspace gas PID tuning\\"

    app = batches = None

    if do_download:
        from hello.hello import HelloApp

        app = HelloApp('192.168.1.4')
        app.login()
        batches = app.getbatches()
    pths = []

    for i in range(1, 4):
        bname = "headspacetest00%d" % i
        fname = os.path.join(pth, "PBS 80 Mesoblast 1 %s.csv" % bname)
        pths.append(fname)
        if do_download:
            dprint("Downloading batch report:", bname)
            bid = batches.getbatchid(bname)
            contents = app.getdatareport_bybatchid(bid)
            with open(fname, 'wb') as f:
                f.write(contents)
    return pths


def run_150128():

    files = download_batches_150128()

    import subprocess
    subprocess.call("tskill.exe excel")

    for file in files:
        main(file)
        print("Analyzed file:", file)


if __name__ == '__main__':
    run_150128()
