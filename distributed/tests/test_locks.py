from __future__ import print_function, division, absolute_import

from time import sleep
import sys

import pytest
from tornado import gen

from distributed import Client, Lock, wait, get_client
from distributed.metrics import time
from distributed.utils_test import (gen_cluster, inc, cluster, slow, div)
from distributed.utils_test import loop # flake8: noqa


@gen_cluster(client=True)
def test_lock(c, s, a, b):
    c.set_metadata('locked', False)
    def f(x):
        client = get_client()
        with Lock('x') as lock:
            assert client.get_metadata('locked') == False
            client.set_metadata('locked', True)
            sleep(0.05)
            assert client.get_metadata('locked') == True
            client.set_metadata('locked', False)

    futures = c.map(f, range(10))
    results = yield futures
    assert not s.extensions['locks'].events
    assert not s.extensions['locks'].ids


@gen_cluster(client=True)
def test_timeout(c, s, a, b):
    locks = s.extensions['locks']
    lock = Lock('x')
    yield lock.acquire()
    lock2 = Lock('x')
    assert lock.id != lock2.id

    start = time()
    with pytest.raises(gen.TimeoutError):
        yield lock2.acquire(timeout=0.1)
    stop = time()
    assert stop - start < 0.3

    yield lock.release()


@gen_cluster(client=True)
def test_acquires_with_zero_timeout(c, s, a, b):
    lock = Lock('x')
    yield lock.acquire(timeout=0)
    assert lock.locked()
    yield lock.release()

    yield lock.acquire(timeout=1)
    yield lock.release()
    yield lock.acquire(timeout=1)
    yield lock.release()


def test_timeout_sync(loop):
    with cluster() as (s, [a, b]):
        with Client(s['address'], loop=loop) as c:
            with Lock('x') as lock:
                with pytest.raises(gen.TimeoutError):
                    Lock('x').acquire(timeout=0.1)


@gen_cluster(client=True)
def test_errors(c, s, a, b):
    lock = Lock('x')
    with pytest.raises(ValueError):
        yield lock.release()
