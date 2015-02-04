"""

Created by: Nathan Starkweather
Created on: 02/02/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from hello import HelloThing
import tkinter as tk
import tkinter.ttk as ttk
from collections import deque


class Viewer(HelloThing):
    def __init__(self, ipv4):
        HelloThing.__init__(self, ipv4)
        self.root = tk.Tk("Agitation Viewer")
        self.frame1 = ttk.LabelFrame(self.root, text="Agitation View")
        # self.frame2 = ttk.LabelFrame(self.root, text="Last Odd Value")
        # self.frame3 = ttk.LabelFrame(self.root, text="Last Even Value")
        self.frame4 = ttk.LabelFrame(self.root, text="Average of last 3")
        self.main_display = tk.Label(self.frame1, text="")
        # self.last_odd = tk.Label(self.frame2, text="")
        # self.last_even = tk.Label(self.frame3, text="")
        self.average = tk.Label(self.frame4, text="")
        self.close_btn = ttk.Button(self.root, text="Close", command=lambda: self.root.destroy())

        c = 1

        def nc():
            nonlocal c
            c += 1
            return c

        self.frame1.grid(row=1, column=nc())
        # self.frame2.grid(row=1, column=nc())
        # self.frame3.grid(row=1, column=nc())
        self.frame4.grid(row=1, column=nc())
        # self.last_odd.grid()
        # self.last_even.grid()
        self.average.grid()
        self.main_display.grid()
        self.close_btn.grid()

        self.buf3 = deque((0 for _ in range(3)), 3)
        self.count = 0
        self.minrpm = 1
        self.pv = 0

        self.update_interval = 1000

    def update(self):
        self.count += 1
        try:
            pv = self._getpv()
            if pv == self.pv:
                return
            self.pv = pv

            strpv = "%.3f" % pv
            if pv < self.minrpm:
                strpv = "(%s)" % strpv
            self.main_display.configure(text=strpv)

            # if self.count % 2:  # if number is odd
            #     self.last_odd.configure(text=strpv)
            # else:
            #     self.last_even.configure(text=strpv)

            self.buf3.append(pv)
            ave = sum(self.buf3) / len(self.buf3)
            str_ave = "%.3f" % ave
            if ave < self.minrpm:
                str_ave = "(%s)" % str_ave
            self.average.configure(text=str_ave)
        finally:
            self.root.after(self.update_interval, self.update)

    def _getpv(self):
        pv = self._app.getagpv()
        return pv

    def main(self):
        self.root.after(500, self.update)
        self.root.mainloop()

if __name__ == '__main__':
    Viewer("192.168.1.4").main()
