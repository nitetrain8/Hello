"""

Created by: Nathan Starkweather
Created on: 09/26/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from io import StringIO, SEEK_END
from datetime import datetime
from traceback import format_exc
from os.path import exists as path_exists, split as path_split
from os import makedirs

_now = datetime.now


class Logger():
    """ Simple logger. Use as mixin or
    class var.

    Overrides:
    var cocroot: directory to store log in
    var _log_name: _log_name prefix for log file
    var savedateformat: strftime compatible date format for log filename
    var logdateformat: strftime compatible date format for each logger entry
    """

    docroot = "C:\\.replcache\\log\\"
    _default_logname = "LoggerLog"
    savedateformat = "%y%m%d%H%M%S"
    logdateformat = "%m/%d/%Y %H:%M:%S"

    def __init__(self, name=''):
        self._log_name = name or self._default_logname
        self._logbuf = StringIO()
        self._closed = False

    def _log(self, *args, **pkw):
        """
        Log stuff. print to console, save a copy to
        internal log buffer.
        """
        now = _now().strftime(self.logdateformat)
        print(now, *args, file=self._logbuf, **pkw)
        print(now, *args)

    log = _log  # mixin alias

    def _log_err(self, *msg, **pkw):
        self._log(*msg, **pkw)
        self._log(format_exc())

    log_err = _log_err  # mixin alias

    def _get_log_name(self):

        root = self.docroot
        if not (root.endswith("\\") or root.endswith("/")):
            root += "\\"

        tmplt = root + "%s %s%%s.log" % (self._log_name, _now().strftime(self.savedateformat))
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
            self._logbuf.seek(0, 0)
            for line in self._logbuf:
                f.write(line)

        self._logbuf = StringIO()

    def close(self):

        if self._closed:
            return

        self._closed = True
        self._commit_log()

    def __del__(self):
        self.close()
