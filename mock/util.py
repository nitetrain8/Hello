"""

Created by: Nathan Starkweather
Created on: 11/07/2014
Created in: PyCharm Community Edition


"""
from functools import wraps

__author__ = 'Nathan Starkweather'


def nextroutine(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        g = f(*args, **kwargs)
        return g.__next__
    return wrapper


def sendroutine(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        g = f(*args, **kwargs)
        next(g)
        return g.send
    return wrapper
