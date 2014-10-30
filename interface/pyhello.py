"""

Created by: Nathan Starkweather
Created on: 10/27/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'


import tkinter as tk
import tkinter.ttk as ttk
from hello import HelloThing


class HelloInterface(HelloThing):
    def __init__(self, app_or_ipv4):
        HelloThing.__init__(self, app_or_ipv4)

        self.root = r = tk.Tk("HELLO{World!}")
        self.frame = ttk.Frame(r)
        self.button = ttk.Button(self.frame)

        self.frame.grid()
        self.button.grid()

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    HelloInterface('71.189.82.196:6').run()
