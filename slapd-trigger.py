#!/usr/bin/env python
# -*- coding: utf-8 mode: python -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8

import os, sys
from os import path
# local libraries
_liblocal = path.join(path.split(__file__)[0], 'lib')
if path.isdir(_liblocal): sys.path.insert(0, _liblocal)

if __name__ == '__main__':
    from slapd_trigger.stmain import run_slapd_trigger
    run_slapd_trigger(__file__)
