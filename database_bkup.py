"""

Created by: Nathan Starkweather
Created on: 08/28/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from shutil import copy2
from os import rename, listdir
from os.path import exists
from datetime import date
from re import compile as re_compile


def find_guis(files):
    guis = [f for f in files if ("gui" in f) and f.endswith(".fmp12")]
    if not guis:
        raise FileNotFoundError("Error: couldn't locate Hello GUI file")
    return guis


def find_most_recent(guis):
    parser = re_compile(".*?(\d+)(?:\s|\.)").match

    last_date = 0
    last_version = 1
    latest = None
    others = []
    for g in guis:
        groups = parser(g).groups()
        date = groups[0]
        try:
            n = int(groups[1])
        except IndexError:
            n = None

        idate = int(date)
        if idate > last_date:
            latest = g
        elif idate == last_date:
            if n is not None and n > last_version:
                latest = g
        else:
            others.append(g)

    return last_version, latest


def backup_gui(dropbox):

    files = listdir(dropbox)
    guis = find_guis(files)
    n, file = find_most_recent(guis)

    today = date.today().strftime("%y%m%d")
    fpth = "HELLO Tests gui %s %%d.fmp12" % today
    new = unique_newname(n, fpth)
    bkup = dropbox + "/archive/" + file

    make_backups('/'.join((dropbox, file)), bkup, '/'.join((dropbox, new)))


def make_backups(old, bkup, new):
    print("Backing up file:", old)
    print("Backing up to:", bkup)
    copy2(old, bkup)
    if new is not None:
        print("Renaming as:", new)
        rename(old, new)
    print("Backup Successful")
    print()


def unique_newname(n, template):
    while True:
        maybe = template % n
        if not exists(maybe):
            return maybe
        n += 1


def backup_data(dropbox):

    files = listdir(dropbox)
    master_data = "HELLO Tests Master Data.fmp12"

    if master_data not in files:
        raise FileNotFoundError("Couldn't find HELLO Tests Master Data")

    today = date.today().strftime("%y%m%d")

    # %%d escapes the format sequence so the next function
    # can format it as %d.
    fpth = "HELLO Tests Data %s %%d.fmp12" % today

    target = unique_newname(1, '/archive/'.join((dropbox, fpth)))

    make_backups('/'.join((dropbox, master_data)), target, None)

if __name__ == '__main__':
    # dropbox = "C:/Users/PBS Biotech/New folder/Dropbox/HELLO Testing"
    dropbox = "."
    backup_gui(dropbox)
    backup_data(dropbox)
    input("Press Enter to close.")

