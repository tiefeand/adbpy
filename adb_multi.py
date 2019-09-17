# ------------------------------------------------------------------------------
# Name:        adb
# Purpose:     provides an interface for adb
#
# Author:      atiefenauer
#
# Created:     01.08.2015
# Copyright:   (c) atiefenauer 2015
# Licence:     <your licence>
# ------------------------------------------------------------------------------
# !/usr/bin/env python
__author__ = "atiefenauer"
__version_info__ = ('1', '0', '0')
__version__ = '.'.join(__version_info__)


from collections import Mapping
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool

from adb import AbstractAdb, all_adb_serialnos, AbstractAdbProcess, AdbProcess, Adb

THREADS = cpu_count()*2


class AdbMultiProcess(AbstractAdbProcess):
    """ executes an adb command to all attached devices or those specified """
    def __init__(self, **adb_single_process):
        if not isinstance(adb_single_process, AdbProcess):
            adb_single_process = AdbProcess(**adb_single_process)
        self.process = adb_single_process

    def execute(self, arg, serialnos=None, **kwargs):
        serialnos = all_adb_serialnos(serialnos=serialnos, **kwargs)
        pool = ThreadPool(THREADS)
        res = list()
        for s in serialnos:
            res.append(pool.apply_async(self.process.execute,
                                        args=(arg,),
                                        kwds={'serialno': s}))
        [r.wait() for r in res]
        out = [r.get() for r in res]
        pool.close()
        return dict(zip(*(serialnos, out)))


class AdbMapping(Mapping, AbstractAdb):
    """ provides an interface to adb

    >>> import tempfile as tf
    >>> import os
    >>> dirpath = tf.gettempdir()
    >>> filepath = os.path.join(dirpath,'test.txt')
    >>> os.remove(filepath) if os.path.exists(filepath) else None
    >>> fileobj = open(filepath, mode='a+')
    >>> fileobj.write('test')
    >>> fileobj.close()

    # change the loglevel to CRITICAL to get no output in doctest
    >>> import logging as log
    >>> log.basicConfig(level=log.DEBUG)

    >>> serialnos = all_adb_serialnos()
    >>> adb = AdbMapping(serialnos=None, wait=True, logger=log)
    >>> set(adb.get_serialno().values()) == set(serialnos)
    True
    >>> adb.push(filepath, '/sdcard/')
    >>> os.remove(filepath)
    >>> adb.pull('/sdcard/test.txt', dirpath)
    >>> open(filepath, mode='r').readlines()
    ['test']
    >>> adb.shell('pwd').values()  # doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS
    ['/'...
    >>> adb.wait_for_device()
    >>> adb.remount()
    >>> adb.root()
    >>> adb[adb.keys()[0]].reboot()
    >>> adb[adb.keys()].reboot()  # doctest: +SKIP
    """
    def __init__(self, adb_multi_process=None, serialnos=None, **kwargs):
        if not isinstance(adb_multi_process, AdbMultiProcess):
            adb_multi_process = AdbMultiProcess(**kwargs)
        self.multi = adb_multi_process
        self.serialnos = serialnos

    def __getitem__(self, serialno):
        if isinstance(serialno, (list, tuple)):
            return AdbMapping(serialnos=serialno, adb_multi_process=self.multi)
        else:
            return Adb(serialno=serialno, adb_single_process=self.multi)

    def __len__(self):
        return len(self.serialnos)

    def __iter__(self):
        if self.serialnos:
            return iter(self.serialnos)
        else:
            return iter(all_adb_serialnos())

    def execute(self, arg):
        return self.multi.execute(arg, serialnos=self.serialnos)


if __name__ == '__main__':
    import doctest
    doctest.testmod()