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


import os
import shlex
import subprocess
import posixpath as px
from collections import Mapping
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool


ADB_PATH = r'adb.exe'
THREADS = cpu_count()*2


def localpath(local):
    """ normalizing local path"""
    return os.path.normpath(local)


def remotepath(remote):
    """ normalizing remote path making sure that a final slash is not removed"""
    remote = remote.strip().replace('\\', '/')
    remote_ = px.normpath(remote)
    return remote_ + px.sep if remote.endswith('/') else remote_


def adb_setpath():
    """ Set environment path variable for adb """
    adbpath = os.environ["LOCALAPPDATA"]+r"\Android\android-sdk\platform-tools"
    os.environ["PATH"] += ";"+adbpath
    return os.system(ADB_PATH)


def sysprocess(cmd):
    """ starting a system process"""
    cmd = cmd.encode('unicode_escape')
    cmd = shlex.split(cmd)
    cmd = ' '.join(cmd)
    ret = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = ''
    stderr = ''
    while ret.returncode is None:
        stdout, stderr = ret.communicate()
    return stdout.strip(), stderr.strip()


def adb_cmd(arg, serialno=None, emulator=False, wait=False, log=None):
    """ Returning the string issued as a system call.

        >>> deviceids = adb_cmd('devices')
        >>> deviceids  # doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS
        ('List of devices attached...', '')
    """
    syscall = '{adb} '.format(adb=ADB_PATH)
    if serialno:
        syscall += '-s {ser} '.format(ser=serialno)
    elif emulator:
        syscall += '-e '
    if wait:
        syscall += 'wait-for-device '
    syscall += arg
    outerr = sysprocess(syscall)
    if log:
        log.debug((syscall, outerr))
    return outerr


def adb_devices(qualifier=None, onlineonly=False):
    devices_ = 'devices '
    if qualifier:
        devices_ += '-l '
    stdout, stderr = adb_cmd(devices_)
    deviceliststr = stdout.strip().splitlines()[1:]
    if onlineonly:
        deviceliststr = filter(lambda l: 'offline' not in l, deviceliststr)
    return dict([ss.split('\t') for ss in deviceliststr])


class Executor(object):
    pass


class AdbExecute(Executor):
    """ Executes an adb command to a specific device, if more than one device
        attached it must receive a serialno
    """
    def __init__(self, wait=False, log=None):
        self.wait = wait
        self.log = log

    def __call__(self, arg, serialno=None):
        return adb_cmd(arg, serialno=serialno, wait=self.wait, log=self.log)

    @staticmethod
    def devices(**kwargs):
        """
        # note that this method can be called before creating an actual instance
        >>> serialno = AdbExecute().devices()  # doctest: +SKIP
        """
        return adb_devices(**kwargs)


def adb_serialnos(serialnos=None, **kwargs):
    """ returns all serial numbers or passes through those who are specified"""
    if serialnos:
        if isinstance(serialnos, (tuple, list)):
            serialnos = serialnos
        else:
            serialnos = [serialnos]
    else:
        serialnos = AdbExecute.devices(**kwargs).keys()
    return serialnos


class AdbMultiExecute(Executor):
    """ Executes an adb command to a specific device, if more than one device
        attached it must receive a serialno
    """
    def __init__(self, **adbexecute):
        self.executor = adbexecute if isinstance(adbexecute, AdbExecute) else AdbExecute(**adbexecute)

    def __call__(self, arg, serialnos=None, **kwargs):
        serialnos = adb_serialnos(serialnos=serialnos, **kwargs)
        pool = ThreadPool(THREADS)
        res = list()
        for s in serialnos:
            res.append(pool.apply_async(self.executor,
                                        args=(arg,),
                                        kwds={'serialno': s}))
        [r.wait() for r in res]
        out = [r.get() for r in res]
        pool.close()
        return dict(zip(*(serialnos, out)))


def get_adbmultiexecute(adbmultiexecute=None, **kwargs):
    if adbmultiexecute:
        a = adbmultiexecute if isinstance(adbmultiexecute, AdbMultiExecute) else AdbMultiExecute(**kwargs)
    else:
        a = AdbMultiExecute(**kwargs)
    return a


class Adb(Mapping):
    """ Provides an interface to adb

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

    >>> serialnos = get_all_adb_serialno()
    >>> adb = Adb(serialnos=None, wait=True, log=log)
    >>> set(dict(adb.get_serialno().values()).keys()) == set(serialnos)
    True
    >>> adb.push(filepath, '/sdcard/')
    >>> os.remove(filepath)
    >>> adb.pull('/sdcard/test.txt', dirpath)
    >>> open(filepath, mode='r').readlines()
    ['test']
    >>> adb.shell('pwd').values()  # doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS
    [('/', '')...
    >>> apk = r'C:\\work\\svn\\Mobile\\Testing\\Data\\UnitTestExamples\\tags\\v1_0_0\\SensorLab\\Sensorlab.apk'
    >>> adb.install(local=apk, reinstall=True)
    >>> adb.uninstall('com.sensirion.sensorlab')
    >>> adb.wait_for_device()
    >>> adb.remount()
    >>> adb.root()
    >>> adb[adb.keys()[0]].reboot()
    >>> adb[adb.keys()].reboot()  # doctest: +SKIP
    """
    def __init__(self, adbmultiexecute=None, serialnos=None, **kwargs):
        self.executor = adbmultiexecute if isinstance(adbmultiexecute, AdbMultiExecute) else AdbMultiExecute(**kwargs)
        self.serialnos = serialnos

    def __getitem__(self, serialno):
        return Adb(serialnos=serialno, adbmultiexecute=self.executor)

    def __len__(self):
        return len(self.serialnos)

    def __iter__(self):
        if self.serialnos:
            return iter(self.serialnos)
        else:
            return iter(self.executor.executor.devices().keys())

    def execute(self, arg):
        return self.executor(arg, serialnos=self.serialnos)

    def wait_for_device(self):
        self.execute('wait-for-device')

    def get_serialno(self):
        return self.execute('get-serialno')
        # stdout, stderr = self.execute('get-serialno')
        # return stdout

    def shell(self, arg):
        shell = "shell '{arg}'".format(arg=arg)
        return self.execute(shell)
        # stdout, stderr = self.execute(shell)
        # return stdout

    def pull(self, remote, local=None):
        local = localpath(local if local else '')
        remote = remotepath(remote)
        pull = 'pull {re} {lo}'.format(re=remote, lo=local)
        self.execute(pull)

    def push(self, local, remote):
        local = localpath(local)
        remote = remotepath(remote)
        push = 'push {lo} {re}'.format(lo=local, re=remote)
        self.execute(push)

    def install(self, local, fwdlock=False, reinstall=False, sdcard=False):
        install = 'install '
        if fwdlock:
            install += '-l '
        if reinstall:
            install += '-r '
        if sdcard:
            install += '-s '
        install += '{local}'.format(local=localpath(local))
        self.execute(install)

    def uninstall(self, package, keepdata=False):
        uninstall = 'uninstall '
        if keepdata:
            uninstall += '-k '
        uninstall += '{package}'.format(package=package)
        self.execute(uninstall)

    def remount(self):
        self.execute('remount')

    def root(self):
        self.execute('root')

    def reboot(self):
        self.execute('reboot')

    def version(self):
        stdout, stderr = self.execute('version')
        return stdout

    def help(self):
        stdout, stderr = self.execute('help')
        return stdout

    @classmethod
    def kill_server(cls):
        cls().execute('kill-server')

    @classmethod
    def start_server(cls):
        cls().execute('start-server')

    def logcat(self):
        raise NotImplementedError

    def bugreport(self):
        raise NotImplementedError

    def jdwp(self):
        raise NotImplementedError

    def forward(self):
        raise NotImplementedError

    def listen(self):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def get_state(self):
        raise NotImplementedError


def get_all_adb_serialno(**kwargs):
    """ returns the serial numbers of all attached devices
    :param kwargs: qualifier, onlineonly
    """
    return adb_serialnos(serialnos=None, **kwargs)


def get_one_adb_serialno(**kwargs):
    """ returns the serialno of the only attached device, exception if too many
    :param kwargs: qualifier, onlineonly
    """
    serialnos = get_all_adb_serialno(**kwargs)
    if len(serialnos) > 1:
        raise Exception('found too many devices')
    return serialnos[0]


# def get_all_adb_connections(wait=False, log=None, **kwargs):
#     serialnos = get_all_adb_serialno(**kwargs)
#     return tuple([Adb(serialno=s, wait=wait, log=log) for s in serialnos])
#
#
# def get_one_adb_connection(wait=False, log=None, **kwargs):
#     serialno = get_one_adb_serialno(**kwargs)
#     return Adb(serialno=serialno, wait=wait, log=log)


if __name__ == '__main__':
    import doctest
    doctest.testmod()