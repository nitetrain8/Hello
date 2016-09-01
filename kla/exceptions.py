"""

Created by: Nathan Starkweather
Created on: 02/03/2016
Created in: PyCharm Community Edition


"""
from hello.hello import HelloError


class KLAError(HelloError):
    pass


class SkipTest(Exception):
    pass
