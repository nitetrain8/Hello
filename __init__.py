"""

Created by: Nathan Starkweather
Created on: 10/15/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'

from .hello import *
from .logger import Logger, PLogger


class HelloThing():
    """
    @type _app: HelloApp
    """
    def __init__(self, app_or_ipv4):

        self._app = None
        self._app_or_ipv4 = app_or_ipv4

    def _init_app(self):

        if self._app is not None and \
                isinstance(self._app, HelloApp):
            return

        if isinstance(self._app_or_ipv4, HelloApp):
            self._app = self._app_or_ipv4
        else:
            self._app = HelloApp(self._app_or_ipv4)
