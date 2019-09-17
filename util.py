# ------------------------------------------------------------------------------
# Name:        util
# Purpose:
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
import time
from glob import glob

from dictarray_mutable import FileDictArray
from ui import cli_askoption, box_askdirectory

CONFIG_FILE = '.\enginefab_config.txt'
LINEITEM = '-'
WIDTH = 80

LABEL_DATABASE_PATH = 'database_path'
LABEL_PHONE_LANGUAGE = 'phone_language'
LABEL_TIMEZONE = 'timezone'


def line(item=None):
    if item:
        return item*WIDTH
    else:
        return LINEITEM*WIDTH


def title(title_, item=None):
    return '\n'+'\n'.join([line(item=item), title_, line(item=item)])


def splitpath(filepath):
    path, filename = os.path.split(filepath)
    name, ext = os.path.splitext(filename)
    return path, name, ext


def joinpath(*args):
    args = tuple([a for a in args if a is not None])
    return os.path.normpath(os.path.join(*args))


def mkdir(path):
    path = os.path.normpath(path)
    if not os.path.exists(path):  # TODO: would also accept a file and then not create the directory
        os.makedirs(path)
    if not os.path.exists(path):
        raise IOError('could not create folder at path:\n{p}'.format(p=path))


def get_timestamp():
    timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
    return timestamp


def listpath(searchpath):
    """ Returns a list of existing path matching the path name pattern. Other
        than glob.glob this function is insensitive to slashes at the end:
        Hence directories are always expanded. Incomplete path names will be
        expanded as if there was a wildcard at the end.

        Returns an empty list if path does not exist or is empty
    """
    searchpath.rstrip(os.path.sep+'*')  # removing eventual separator and '*'
    searchpath = os.path.normpath(searchpath)  # important so that exists() works
    if os.path.isdir(searchpath) and os.path.exists(searchpath):  # add separator if directory
        searchpath = '{sp}{sep}'.format(sp=searchpath, sep=os.path.sep)
    return map(os.path.normpath, glob('{sp}*'.format(sp=searchpath)))  # expand in wildcardmanner


def listfile(searchpath, extension=None):
    """ Returns a list as listpath but returns only existing file path.
        If an extension is given the only file path with this extension are
        returned
    """
    out = listpath(searchpath)
    filelist = []
    for ff in out:
        if os.path.isfile(ff) and has_ext(path=ff, extension=extension):
            filelist.append(ff)
    return filelist


def has_ext(path, extension=None):
    """ Checks whether path looks like a file path with an extension at the
        end (does not check if exists). Checks a specific extension if given.

        Note that if a "." appears in the name of the lowest folder it is
        also mistaken as an extension
    """
    ext = os.path.splitext(path)[1].lstrip('*.')
    if extension is None:
        extension = ext
    if ext is not '' and ext == extension.lstrip('.'):
        return True
    else:
        return False


def filterfilename(path, filtertext=None):
    """ """
    filtertext = filtertext if filtertext else ''
    filelist = glob(joinpath(path, ''.join(['*', filtertext, '*'])))
    return filelist


def filterfilesize(pathlist, minsize=None):
    """ """
    minsize = minsize if minsize else 0
    return [f for f in pathlist if os.path.getsize(f) > minsize]


def create_configfile():
    print '... please choose a path to save registration files using the pop up window'
    entry = {}
    msg = 'please choose a database path'
    entry.update({LABEL_DATABASE_PATH: box_askdirectory(msg)})
    entry.update({LABEL_PHONE_LANGUAGE: cli_askoption(msg, ['english'])})
    entry.update({LABEL_TIMEZONE: cli_askoption(msg, ['Europe/Zurich', 'Asia/Seoul'])})
    with FileDictArray(open(CONFIG_FILE, mode='w+')) as table:
        table.append(entry)
    return table


def read_configfile():
    with FileDictArray(open(CONFIG_FILE, mode='a+')) as filetable:
        pass
    if not filetable:
        filetable = create_configfile()
    return filetable  # returns a closed filetable
