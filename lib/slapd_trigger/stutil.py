# -*- coding: utf-8 mode: python -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8

__all__ = (
    'isseq', 'isint', 'isnumstr',
    'TRACE', 'validate_loglevel', 'init_log',
    'print_exception', 'print_error', 'print_info', 'print_debug', 'print_trace',
    'log_trace',
    'chown', 'chmod',
    )

import sys, os, re, traceback, logging, pwd, grp

def isseq(v): return type(v) in (list, tuple)
def isint(v): return type(v) in (int, long)
RE_NUMERIC = re.compile(r'\d+$')
def isnumstr(v): return RE_NUMERIC.match(v) is not None

TRACE = 1; logging.addLevelName(TRACE, 'TRACE')
LOGLEVEL_MAP = {'WARN': 'WARNING'}
VALID_LOGLEVELS = ('TRACE', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'FATAL')
def validate_loglevel(loglevel):
    ll = str(loglevel).upper()
    if isnumstr(ll): return int(ll)
    ll = LOGLEVEL_MAP.get(ll, ll)
    if ll == 'TRACE': return 1
    elif ll in VALID_LOGLEVELS: return getattr(logging, ll)
    else: raise ValueError("Invalid loglevel: %r" % loglevel)

def init_log(logfile, loglevel, logformat):
    if logfile in (None, '-', '/dev/stderr'):
        logging.basicConfig(stream=sys.stderr, format=logformat, level=loglevel)
    elif logfile == '/dev/stdout':
        logging.basicConfig(stream=sys.stdout, format=logformat, level=loglevel)
    else:
        logging.basicConfig(filename=logfile, format=logformat, level=loglevel)

def print_exception(msg, *args, **kw):
    print "ERRROR:",
    print msg % args
    traceback.print_exc()
def print_error(msg, *args, **kw):
    print "ERROR:",
    print msg % args
def print_info(msg, *args, **kw):
    print "INFO:",
    print msg % args
def print_debug(msg, *args, **kw):
    print "DEBUG:",
    print msg % args
def print_trace(msg, *args):
    print "TRACE:",
    print msg % args
def log_trace(msg, *args, **kw):
    logging.log(TRACE, msg, *args, **kw)

RE_USER_GROUP = re.compile(r'([a-zA-Z0-9_-]*)(?::([a-zA-Z0-9_-]*))?$')
def chown(pf, ug):
    """Change owner and/or group of a file
    """
    mo = RE_USER_GROUP.match(ug)
    if mo is None: raise ValueError("Invalid user/group: %r" % ug)
    user = mo.group(1)
    group = mo.group(2)
    if not user and not group: raise ValueError("Either user or group are required")

    try:
        if not user:
            uid = -1
        elif isnumstr(user):
            # user is a number
            u = pwd.getpwuid(int(user))
            uid = u.pw_uid
        else:
            # user is a name
            u = pwd.getpwnam(user)
            uid = u.pw_uid

        if group is None:
            # ug=='user' so only set user, don't set group
            gid = -1
        elif group == "":
            # ug=='user:' so set user and group, select user default group
            gid = u.pw_gid
        elif isnumstr(group):
            # ug=='user:gid'
            g = grp.getgrgid(int(group))
            gid = g.gr_gid
        else:
            # ug=='user:group'
            g = grp.getgrnam(group)
            gid = g.gr_gid

        if uid != -1 or gid != -1: os.chown(pf, uid, gid)
    except:
        logging.exception("chown")

def chmod(pf, mode):
    """Change mode of a file.
    Either a value from the stat module, or an octal numeric string are supported.
    For example, to change the mode to rwxrwxr-x, one can use:
        chmod(pf, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
    or
        chmod(pf, '775')
    """
    try:
        if not isint(mode): mode = int(str(mode), 8)
        os.chmod(pf, mode)
    except:
        logging.exception("chown")
