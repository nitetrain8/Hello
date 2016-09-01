"""

Created by: Nathan Starkweather
Created on: 10/24/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'


def next_coroutine(f):
    def func(*args, **kwargs):
        g = f(*args, **kwargs)
        next(g)
        return g.__next__
    return func


@next_coroutine
def Timer():
    from time import time
    start = time()
    while True:
        yield time() - start
