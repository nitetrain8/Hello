"""

Created by: Nathan Starkweather
Created on: 04/09/2015
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

import json


def main():
    pth = "C:\\.replcache\\gmv.json"
    names = "Agitation", "Temperature", "DO", "pH", "Condensor", "Level", "Pressure"
    fields = "sp", "pv", "man", "manup", "mandown", "mode", "error", "interlock"
    sensors = "ag", "temp", "do", "ph", "condensor", "level", "pressure"

    from collections import OrderedDict
    out = OrderedDict()
    for s in sensors:
        for f in fields:
            id = s + f
            out[id] = "%.2f"
    with open(pth, 'w') as f:
        json.dump(out, f, indent=4)

if __name__ == '__main__':
    main()
