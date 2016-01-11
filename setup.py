#!/usr/bin/env python
# -*- coding: utf-8 mode: python -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8

NAME = 'slapd-trigger'
VERSION = None
DESCRIPTION = 'Server for the slapd back-sock overlay'
AUTHOR = 'Jephte CLAIN'
EMAIL = 'Jephte.Clain@univ-reunion.fr'
MODULES = ()
SRCDIR = 'lib/slapd_trigger'
PACKAGE_DIR = {'': '.', 'slapd_trigger': SRCDIR}
PACKAGE_DATA = {}
PACKAGES = []
SCRIPTS = ['slapd-trigger.py']

import os, sys, re, fnmatch
from os import path

RE_VERSION = re.compile(r'(\d+(?:\.\d+)*)(?:-r(\d+/\d+/\d+))?')
def get_version(basedir=None):
    if basedir is None:
        basedir = path.split(path.abspath(sys.argv[0]))[0]
    version_txt = path.join(basedir, 'VERSION.txt')
    if not path.isfile(version_txt): return ''
    try:
        inf = open(version_txt, 'rb')
        try: line = inf.readline()
        finally: inf.close()
    except:
        return ''
    mo = RE_VERSION.match(line)
    if not mo: return ''
    return mo.group(1)

def findf(spec, bp):
    """Transformer le package bp en chemin, puis chercher récursivement les
    fichiers correspondant à la spécification spec à partir de SRCDIR/bp
    """
    files = []
    bp = bp.replace(".", "/")
    bpdir = path.join(SRCDIR, bp)
    bpnames = os.listdir(bpdir)
    for specname in fnmatch.filter(bpnames, spec):
        specfile = path.join(bpdir, specname)
        if path.isfile(specfile):
            files.append(specname)
        else:
            for dirpath, dirnames, filenames in os.walk(specfile):
                dirnames.remove('.svn')
                dirpath = dirpath[len(bpdir)+1:]
                files.extend([path.join(dirpath, filename) for filename in filenames])
    return files

def fixp(p, bp):
    """Transformer le package bp en chemin, puis exprimer le chemin relatif p
    par rapport au chemin du package, puis ajouter SRCDIR/ devant le chemin
    """
    bp = bp.replace(".", "/")
    return path.join(SRCDIR, bp, p)
def addp(name, data=()):
    """Ajouter un package, avec ses fichiers de données
    """
    global PACKAGES, PACKAGE_DATA
    PACKAGES.append(name)
    if data:
        files = []
        for spec in data:
            files.extend(findf(spec, name))
        PACKAGE_DATA[name] = files
def adds(name, scripts=()):
    """Ajouter des scripts contenus dans un package
    """
    global SCRIPTS
    if scripts:
        SCRIPTS.extend(map(lambda s: fixp(s, name), scripts))

if VERSION is None: VERSION = get_version()
addp('slapd_trigger')

if __name__ == '__main__':
    from distutils.core import setup
    setup(name=NAME, version=VERSION,
          description=DESCRIPTION, author=AUTHOR, author_email=EMAIL,
          py_modules=MODULES,
          package_dir=PACKAGE_DIR, package_data=PACKAGE_DATA, packages=PACKAGES,
          scripts=SCRIPTS,
          )
