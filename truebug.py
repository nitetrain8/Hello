"""

Created by: Nathan Starkweather
Created on: 06/06/2014
Created in: PyCharm Community Edition


"""
__author__ = 'Nathan Starkweather'


try:
    from hello import HelloApp
except ImportError:
    from hello.hello import HelloApp


def coroutine(f):
    def routine(*args, **kwargs):
        rv = f(*args, **kwargs)
        next(rv)
        return rv.send
    return routine


def _getUsers(app, attempts, expected):
    msg = expected
    n = 0
    while msg == expected and n < 100:
        print("Getting Users:", end=' ')
        msg = app.getUsers()
        n += 1
        attempts += 1
        print(msg, "Attempts:", attempts)
    return msg, attempts


def run_till_true():
    attempts = 1
    app = HelloApp('192.168.1.6')
    expected = app.getUsers()

    if expected == 'True':
        print("Derp", expected)
        return

    while True:
        try:
            app = HelloApp('192.168.1.6')
            msg, attempts = _getUsers(app, attempts, expected)
        except Exception:
            raise
        if msg == 'True':
            break


if __name__ == '__main__':
    run_till_true()
