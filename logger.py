"""

Created by: Nathan Starkweather
Created on: 09/26/2014
Created in: PyCharm Community Edition


"""
from pysrc.snippets.safe_write import safe_pickle

__author__ = 'Nathan Starkweather'

from io import StringIO
from datetime import datetime
from traceback import format_exc
from os.path import exists as path_exists, split as path_split
from os import makedirs

_now = datetime.now


class Logger():
    """ Simple logger. Use as mixin or
    class var.

    Overrides:
    var _cacheroot: directory to store log in
    var _log_name: _log_name prefix for log file
    var _savedateformat: strftime compatible date format for log filename
    var _logdateformat: strftime compatible date format for each logger entry
    """

    _cacheroot = "C:\\.replcache\\"
    _docroot = _cacheroot + "log\\"
    _default_logname = "LoggerLog"

    # used log *filename*
    _savedateformat = "%m-%d-%Y %H-%M"

    # used for each line in log entry
    _logdateformat = "%m/%d/%Y %H-%M-%S"

    def __init__(self, name=''):
        self._log_name = name or self._default_logname
        self._logbuf = StringIO()
        self._closed = False

    def set_logname(self, name):
        self._log_name = name

    def set_save_date_format(self, fmt):
        self._savedateformat = fmt

    def set_docroot(self, root):
        self._docroot = root

    def set_log_date_format(self, fmt):
        self._logdateformat = fmt

    def reopen(self):
        if not self._closed:
            self.close()

        self._logbuf = StringIO()
        self._closed = False

    def _log(self, *args, **pkw):
        """
        Log stuff. print to console, save a copy to
        internal log buffer. Uses print() instead of write()
        so that _log() and _log_err() can be used exactly
        the same way that print() is.
        """

        if self._closed:
            raise ValueError("Logger is closed. Call reopen before logging")

        now = _now().strftime(self._logdateformat)

        # Adding tab to make this (in theory) easy to parse
        # via string.split('\t') or regex to extract data from log
        
        if pkw.pop("reuse_line", False):
            pkw['end'] = ""
            now = "\r" + now
        
        print(now, "\t", *args, file=self._logbuf, **pkw)
        print(now, "\t", *args, **pkw)

    def _log_err(self, *msg, **pkw):
        self._log(*msg, **pkw)
        self._log(format_exc())
        
    # Pickle support
        
    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_logbuf']
        return state
        
    def __setstate__(self, state):
        self.__dict__.update(state)
        self._logbuf = StringIO()

    def _get_log_name(self):

        root = self._docroot
        if not (root.endswith("\\") or root.endswith("/")):
            root += "\\"

        tmplt = root + "%s %s%%s.log" % (self._log_name, _now().strftime(self._savedateformat))
        fpth = tmplt % ''
        n = 1
        while path_exists(fpth):
            fpth = tmplt % (' ' + str(n))
            n += 1
        return fpth, 'w'

    def _commit_log(self):
        fpth, mode = self._get_log_name()

        dirname = path_split(fpth)[0]
        try:
            makedirs(dirname)
        except FileExistsError:
            pass

        # just in case the log is really big, avoid derping
        # the whole thing into memory at once.
        with open(fpth, mode) as f:
            self._logbuf.seek(0, 0)  # beginning of file
            for line in self._logbuf:
                f.write(line)

        del self._logbuf

    def close(self):

        if self._closed:
            return

        self._closed = True
        self._commit_log()

    def __del__(self):
        self.close()


class PLogger(Logger):
    def close(self):
        if self._closed:
            return

        self._closed = True
        self._commit_log()
        self._pickle_self()

    def _get_pickle_name(self):
        root = self._cacheroot
        if not (root.endswith("\\") or root.endswith("/")):
            root += "\\"

        tmplt = root + "%s %s%%s.pkl" % (self._log_name, _now().strftime(self._savedateformat))
        fpth = tmplt % ''
        n = 1
        while path_exists(fpth):
            fpth = tmplt % (' %s' % n)
            n += 1
        return fpth

    def _pickle_self(self):
        fpth = self._get_pickle_name()
        safe_pickle(self, fpth)


import logging


class BuiltinLogger(logging.Logger):
    _docroot = "C:\\.replcache\\log\\"

    def __init__(self, name, level=logging.DEBUG, path=_docroot):
        logging.Logger.__init__(self, name, level)

        import sys
        import os

        h1 = logging.StreamHandler(sys.stderr)
        h2 = logging.FileHandler(os.path.join(path, name + ".log"))
        f = logging.Formatter("%(asctime)s %(levelname)s <%(funcName)s>: %(message)s",
                              logging.Formatter.default_time_format)

        for h in (h1, h2):
            self.addHandler(h)
            h.setLevel(level)
            h.setFormatter(f)


