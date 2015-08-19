import os
from officelib.xllib import xlcom


# def copy(xl, wb):
#     for wb2 in xl.Workbooks:
#         if wb2.Name == wb.Name:
#             continue
#         ws = wb.Worksheets.Add()
#         ws2 = wb2.Worksheets(1)
#         rng = ws2.UsedRange
#         lastrow = rng.Rows.Count
#         lastcol = rng.Columns.Count
#         ws.Cells.Range(ws.Cells(1, 1), ws.Cells(lastrow, lastcol)).Value = rng.Value
#         try:
#             ws.Name = wb2.Name.replace("(", "").replace(")", "")
#         except:
#             print(wb2.Name)
#
#
# def clear_ws(wb):
#     while wb.Worksheets(1):
#         if wb.Worksheets.Count == 1:
#             break
#         wb.Worksheets(1).Delete()
#
#
# def to_master(wb):
#     try:
#         ws = wb.Worksheets("All")
#     except:
#         ws = wb.Worksheets.Add()
#         ws.Name = "All"
#
#     col = 1
#     for ws2 in wb.Worksheets:
#         if ws2.Name == "All":
#             continue
#
#         data = ws2.UsedRange
#         rows = data.Rows.Count
#
#         ws.Cells.Range(ws.Cells(2, col), ws.Cells(rows + 1, col + 1)).Value = data.Value
#         ws.Cells(1, col).Value = ws2.Name
#
#         col += 3
#
#
# def copy_ws(from_ws, to_ws):
#     rng = from_ws.UsedRange
#     lastrow = rng.Rows.Count
#     lastcol = rng.Columns.Count
#     to_ws.Cells.Range(to_ws.Cells(1, 1), to_ws.Cells(lastrow, lastcol)).Value = rng.Value
#
#
# def get_ws_name(name):
#     name = os.path.basename(name)
#     name = os.path.splitext(name)[0]
#     name = name.replace("(", "").replace(")", "").replace(".txt", "")
#     return name
#
#
# def copy_data(from_ws, to_ws, col, name):
#     rng = from_ws.UsedRange
#     rows = rng.Rows.Count
#     to_rng = to_ws.Cells.Range(to_ws.Cells(2, col), to_ws.Cells(rows + 1, col + 1))
#     to_rng.Value = rng.Value
#
#     to_ws.Cells(1, col).Value = name
#     to_ws.Cells(2, col).Value = "Time(ticks)"
#     to_ws.Cells(2, col + 1).Value = "RPM"
#
#     for col in to_rng.Columns:
#         try:
#             col.EntireColumn.AutoFit()
#         except:
#             import pdb
#             pdb.set_trace()
#
#
# def _import_file(col, file, ws1, xl):
#     """
#     @param col:
#     @param file: *full filepath*
#     @param ws1:
#     @param xl:
#     @return:
#
#     Mutually recursive import function with _import_path
#     """
#     try:
#         _, wb = xlcom.xlBook2(file, visible=False, xl=xl)
#     except:
#         import traceback
#         traceback.print_exc()
#         return col
#     ws = wb.Worksheets(1)
#
#     # data transfer
#     name = get_ws_name(file)
#     copy_data(ws, ws1, col, name)
#
#     col += 3
#     wb.Close(False)
#     return col
#
#
# def _import_path(col, ws1, xl, path):
#     """
#     @param col:
#     @param ws1:
#     @param xl:
#     @param path:
#     @return:
#
#     Mutually recursive import function with _import_file.
#     """
#     for file in os.listdir(path):
#         full_path = os.path.join(path, file)
#         if os.path.isdir(full_path):
#             col = _import_path(col, ws1, xl, full_path)
#         else:
#             col = _import_file(col, full_path, ws1, xl)
#     return col
#
#
# def _begin_import():
#     xl, wb = xlcom.xlBook2()
#     while wb.Worksheets.Count > 1:
#         wb.Worksheets(1).Delete()
#     ws1 = wb.Worksheets(1)
#     return xl, wb, ws1
#
#
# def import_file(file):
#     xl, wb, ws1 = _begin_import()
#     _import_file(1, file, ws1, xl)
#
#
# def import_files(*files):
#     xl, wb, ws1 = _begin_import()
#     col = 1
#     for file in files:
#         col = _import_file(col, file, ws1, xl)
#
#
# def import_path(path):
#     xl, wb, ws1 = _begin_import()
#
#     xl.Visible = False
#     try:
#         _import_path(1, ws1, xl, path)
#     finally:
#         xl.Visible = True
#
#     wb.Activate()
        

class Importer():
    def __init__(self):
        self.xl = None
        self.wb = None
        self.ws1 = None

    def import_path(self, path):
        self.xl, self.wb, self.ws1 = self._begin_import()

        self.xl.Visible = False
        try:
            self._import_path(1, path)
        finally:
            self.xl.Visible = True

        self.wb.Activate()

    def finish(self):
        self.xl = None
        self.wb = None
        self.ws1 = None

    def _import_path(self, col, path):
        """
        @param col:
        @param path:
        @return:

        Mutually recursive import function with _import_file.
        """
        for file in os.listdir(path):
            full_path = os.path.join(path, file)
            if os.path.isdir(full_path):
                col = self._import_path(col, full_path)
            else:
                col = self._import_file(col, full_path)
        return col

    def _import_file(self, col, file):
        """
        @param col:
        @param file: *full filepath*
        @return:

        Mutually recursive import function with _import_path
        """
        try:
            _, wb = xlcom.xlBook2(file, visible=False, xl=self.xl)
        except:
            import traceback

            traceback.print_exc()
            return col
        ws = wb.Worksheets(1)

        # data transfer
        name = self.get_ws_name(file)
        self.copy_data(ws, ws1, col, name)

        col += 3
        wb.Close(False)
        return col

    def _begin_import(self):
        xl, wb = xlcom.xlBook2()
        while wb.Worksheets.Count > 1:
            wb.Worksheets(1).Delete()
        ws1 = wb.Worksheets(1)
        return xl, wb, ws1

    def get_ws_name(self, name):
        name = os.path.basename(name)
        name = os.path.splitext(name)[0]
        name = name.replace("(", "").replace(")", "").replace(".txt", "")
        return name


    def copy_data(self, from_ws, to_ws, col, name):
        rng = from_ws.UsedRange
        rows = rng.Rows.Count
        to_rng = to_ws.Cells.Range(to_ws.Cells(2, col), to_ws.Cells(rows + 1, col + 1))
        to_rng.Value = rng.Value

        to_ws.Cells(1, col).Value = name
        to_ws.Cells(2, col).Value = "Time(ticks)"
        to_ws.Cells(2, col + 1).Value = "RPM"

        for col in to_rng.Columns:
            try:
                col.EntireColumn.AutoFit()
            except:
                import pdb
                pdb.set_trace()
