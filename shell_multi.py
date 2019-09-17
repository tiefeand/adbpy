# ------------------------------------------------------------------------------
# Name:        shell
# Purpose:     provides an interface for shell commands via adb
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

import posixpath as px
from time import strftime

from adb import Adb, remotepath


class AbstractShell(object):
    def execute(self, arg):
        raise NotImplementedError

    def su(self, command=None, login=None):
        su = 'su '
        if login is not None:
            su += '-l {login} '.format(login=login)
            raise NotImplementedError
            # TODO: In order to log in, an interactive shell is needed
        if command is not None:
            su += '-c {command}'.format(command=command)
        return self.execute(su)

    def ls(self, remote, longlisting=False):
        remote_ = remotepath(remote).strip('/') + px.sep
        ls = 'ls '
        if longlisting:
            ls += '-l'
        ls += ' \'{remote}\''.format(remote=remote_)
        return self.execute(ls)

    def mkdir(self, remote):
        remote_ = remotepath(remote)
        self.execute('mkdir \'{remote}\''.format(remote=remote_))

    def chmod(self, remote, ugo, recursive=False):
        permissions = {'0': '---',
                       '1': '--x',
                       '2': '-w-',
                       '3': '-wx',
                       '4': 'r--',
                       '5': 'r-x',
                       '6': 'rw-',
                       '7': 'rwx'
                       }
        chmod = 'chmod'
        if recursive:
            chmod += ' -R'
        chmod += ' {ugo}'.format(ugo=str(ugo))
        remote_ = remotepath(remote)
        chmod += ' \'{remote}\''.format(remote=remote_)
        self.execute(chmod)

    def cp(self, origin, destination, recursive=False, force=False):
        cp = 'cp'
        if recursive:
            cp += ' -r'
        if force:
            cp += ' -f'
        orig_ = remotepath(origin)
        dest_ = remotepath(destination)
        self.execute('{cp} \'{orig}\' \'{dest}\''.format(cp=cp, orig=orig_, dest=dest_))

    def mv(self, origin, destination):
        origin_ = remotepath(origin)
        dest_ = remotepath(destination)
        mv = 'mv \'{orig}\' \'{dest}\''.format(orig=origin_, dest=dest_)
        self.execute(mv)

    def rm(self, remote, recursive=False, force=False):
        rm = 'rm'
        if recursive:
            rm += ' -r'
        if force:
            rm += ' -f'
        remote_ = remotepath(remote)
        self.execute('{rm} \'{remote}\''.format(rm=rm, remote=remote_))

    def mount(self, remote, rw_remount=False):
        mount = 'mount'
        if rw_remount:
            mount += ' -o rw,remount'
        remote_ = remotepath(remote)
        self.execute('{mount} \'{remote}\''.format(mount=mount, remote=remote_))

    def echo(self, content):
        kwargs.update(superuser=False)  # su must always be False for echo
        return self.execute('echo \'{content}\''.format(content=str(content).encode('unicode_escape')))

    def redirect(self, content, remote, append=False):
        redirect = 'echo \'{content}\' >'.format(content=str(content).encode('unicode_escape'))
        if append:
            redirect += '>'  # will create >> instead of >
        remote_ = remotepath(remote)
        kwargs.update(superuser=False)  # su must always be False for echo
        self.execute('{redirect} \'{remote}\''.format(redirect=redirect, remote=remote_))

    def cat(self, remote):
        remote_ = remotepath(remote)
        return self.execute('cat \'{remote}\''.format(remote=remote_))

    def getprop(self, prop):
        return self.execute('getprop {prop}'.format(prop=prop))

    def setprop(self, prop, value):
        setprop = 'setprop {prop} {value}'.format(prop=prop, value=value)
        self.execute(setprop)

    def date(self, setmode=False, datetime=None):
        date = 'date'
        if setmode:
            if datetime:
                tstamp = strftime('%Y%m%d.%H%M%S', datetime)
            else:
                tstamp = strftime('%Y%m%d.%H%M%S')
            date += ' -s {timestamp}'.format(timestamp=tstamp)
        stdout = self.execute('{date}'.format(date=date))
        if not setmode:
            return stdout

    def setenforce(self, permissive=False):
        setenforce = 'setenforce'
        if permissive:
            setenforce += ' 0'.format(mode='0')
        else:
            setenforce += ' 1'.format(mode='1')
        self.execute(setenforce)

    def stop(self):
        self.execute('stop')

    def start(self):
        self.execute('start')

    def sleep(self, seconds):
        sleep = 'sleep {seconds}'.format(seconds=seconds)
        self.execute(sleep)


class AbstractShellProcess(object):
    pass


class ShellSingleProcess(object):
    def __init__(self, adb=None, superuser=False, **kwargs):
        self.adb = adb if isinstance(adb, Adb) else Adb(**kwargs)
        self.superuser = superuser

    def execute(self, arg):
        if self.superuser:
            out = Shell(self.adb).su(command=arg)
        else:
            out = self.adb.shell(arg)
        return out


class Shell(AbstractShell):
    """

    # change the loglevel to DEBUG or higher to get no output in doctest
    >>> import logging as log
    >>> log.basicConfig(level=log.DEBUG)

    >>> adb = Adb(wait=True, log=log)
    >>> sh = Shell(adb)
    >>> originpath = 'sdcard/mkdir'
    >>> sh.rm(originpath, force=True, recursive=True)

    #>>> sh.isdirectory(originpath)
    False
    >>> sh.mkdir(originpath)

    #>>> sh.isdirectory(originpath)
    True
    >>> origin = originpath+'/test.txt'
    >>> sh.rm(origin, force=True, superuser=True)

    #>>> sh.isfile(origin)
    False
    >>> sh.redirect('abc', origin, superuser=True)

    #>>> sh.isfile(origin)
    True

    >>> destinationpath = '/system/lib'
    >>> sh.mount('/system', rw_remount=True, superuser=True)
    >>> sh.chmod(destinationpath, '755', superuser=True)
    >>> destination = destinationpath+'/test.txt'
    >>> sh.rm(destination, force=True, superuser=True)
    >>> sh.cp(origin, destination)
    >>> sh.cat(destination).values()  # doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS
    [('abc', '')...
    >>> sh.chmod(destination, '744', superuser=True)

    >>> sh.ls(destinationpath, longlisting=True, superuser=True).values()  # doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS
    [('...root...

    #>>> l1.extract('permissions', name='test.txt').item()
    '-rwxr--r--'
    >>> sh.chmod(destination, '755', superuser=True)

    >>> sh.ls(destinationpath, longlisting=True, superuser=True).values()  # doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS
    [('...root...

    #>>> l2.extract('permissions', name='test.txt').item()
    '-rwxr-xr-x'

    >>> sh.su(command='start').values()  # doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS
    [('', '')...
    >>> sh.setprop('persist.sys.timezone', 'Asia/Seoul', superuser=True)
    >>> sh.getprop('persist.sys.timezone').values()  # doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS
    [('Asia/Seoul', '')...
    >>> sh.setprop('persist.sys.timezone', 'Europe/Zurich', superuser=True)
    >>> sh.getprop('persist.sys.timezone').values()  # doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS
    [('Europe/Zurich', '')...
    >>> sh.date(setmode=True, datetime=(2010,12,31,12,01,59,7,365,0), superuser=True)
    >>> sh.setenforce(permissive=True, superuser=True)
    >>> sh.stop()
    >>> sh.start()
    >>> sh.sleep(1)
    >>> sh.rm(originpath, force=True, recursive=True, superuser=True)
    >>> sh.rm(destination, force=True, superuser=True)
    >>> sh[sh.keys()[0]].echo('only one device returns an echo').values()
    [('only one device returns an echo', '')]
    """
    def __init__(self, adb=None, **kwargs):
        self.executor = adb if isinstance(adb, ShellSingleProcess) else ShellSingleProcess(adb, **kwargs)

    def __getitem__(self, serialno):
        adb = Adb(serialnos=serialno, adbmultiexecute=self.executor.adb.executor)
        return Shell(adb)

    def __len__(self):
        return len(self.executor.adb)

    def __iter__(self):
        return iter(self.executor.adb)

    def execute(self, arg, **kwargs):
        return self.executor(arg, **kwargs)


def get_shell_from_serialno(serialno=None, **kwargs):
    """
    :param kwargs: serialno, wait, log
    :return:
    """
    adb = serialno if isinstance(serialno, Adb) else Adb(serialno=serialno, **kwargs)
    return Shell(adb)


if __name__ == '__main__':
    import doctest
    doctest.testmod()