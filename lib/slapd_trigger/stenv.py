# -*- coding: utf-8 mode: python -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8

__all__ = (
    'Env',
    'validate_logfile', 'validate_loglevel', 'validate_server',
    )

import os, sys, re, logging, atexit
from os import path
from signal import signal, getsignal, SIGINT, SIGTERM

from stutil import *
from strules import *
from stworker import *

def validate_logfile(logfile):
    if logfile == '-' or logfile == '/dev/stderr': return None
    else: return logfile

RE_SPARAM_NAME=re.compile(r'(bindmethod|binddn|saslmech|authcid|authzid|realm|credentials)=')
RE_SIMPLE_VALUE=re.compile(r'([^\s"]*)\s*')
RE_QUOTED_VALUE=re.compile(r'(\\[^"\\])|(\\\\)|((?:\\\\)*\\")|([^"\\]+)')
RE_EOS = re.compile(r'"\s*')
def parse_sparam_name(s):
    if s == '':
        return '', ''
    mo = RE_SPARAM_NAME.match(s)
    if mo is not None:
        s = s[mo.end(0):]
        return mo.group(1), s
    raise ValueError("Invalid string: %r" % s)
def parse_sparam_value(s):
    if s == '':
        return '', ''
    elif s[0] == '"':
        values = []
        s = s[1:]
        while True:
            mo = RE_QUOTED_VALUE.match(s)
            if mo is not None:
                qq = mo.group(1)
                q2 = mo.group(2)
                q2qq = mo.group(3)
                value = mo.group(4)
                s = s[mo.end(0):]
                if qq is not None:
                    values.append(qq)
                elif q2 is not None:
                    values.append('\\')
                elif q2qq is not None:
                    values.append(((len(q2qq) - 2) / 2) * '\\')
                    values.append('"')
                elif value is not None:
                    values.append(value)
                else: #bug
                    raise ValueError("Unexpected value")
                continue
            mo = RE_EOS.match(s)
            if mo is not None:
                s = s[mo.end(0):]
                break
            raise ValueError("Invalid string: %r" % s)
        return ''.join(values), s
    else:
        mo = RE_SIMPLE_VALUE.match(s)
        if mo is None: raise ValueError("Invalid string: %r" % s)
        value = mo.group(1)
        s = s[mo.end(0):]
        return value, s
def validate_server(server=None, ldapuri=None, simpleauth=None, binddn=None,
                    saslmech=None, authcid=None, authzid=None, realm=None,
                    credentials=None):
    config = {}
    if server is not None:
        simpleauth = binddn = saslmech = authcid = authzid = realm = credentials = None
        ldapuri, s = parse_sparam_value(server)
        while s:
            name, s = parse_sparam_name(s)
            if not s: break
            value, s = parse_sparam_value(s)
            if name == 'bindmethod':
                if value == 'simple': simpleauth = True
                elif value == 'sasl': simpleauth = False
                else: raise ValueError("Invalid value for bindmethod: %r" % value)
            elif name == 'binddn':
                binddn = value
            elif name == 'saslmech':
                saslmech = value
            elif name == 'authcid':
                authcid = value
            elif name == 'authzid':
                authzid = value
            elif name == 'realm':
                realm = value
            elif name == 'credentials':
                credentials = value
            else: #bug
                raise ValueError("Unexpected value")

    if ldapuri is None:
        ldapuri = 'ldapi://'
    if simpleauth is None:
        if saslmech is not None:
            simpleauth = False
            binddn = None
        elif binddn is not None:
            simpleauth = True
            authcid = authzid = realm = None
        else:
            simpleauth = False
            saslmech = 'EXTERNAL'
    config = dict(ldapuri=ldapuri, simpleauth=simpleauth, credentials=credentials)
    if saslmech is not None:
        config.update(saslmech=saslmech, authcid=authcid, authzid=authzid, realm=realm)
    elif binddn is not None:
        config.update(binddn=binddn)
    return config

class Env:
    inf = None
    outf = None

    state = None
    rules = None

    devel = None
    devel_ldif_output = None
    logfile = None
    loglevel = logging.INFO
    logformat = '%(levelname)s %(asctime)s %(message)s'
    pidfile = None
    socket_path = None
    socket_owner = None
    socket_mode = None
    server = None
    vars = None
    worker = None

    logenabled = None
    def exception(self, msg, *args, **kw):
        if self.logenabled: logging.exception(msg, *args, **kw)
        elif self.loglevel <= logging.ERROR: print_exception(msg, *args)
    def error(self, msg, *args, **kw):
        if self.logenabled: logging.error(msg, *args, **kw)
        elif self.loglevel <= logging.ERROR: print_error(msg, *args)
    def info(self, msg, *args, **kw):
        if self.logenabled: logging.info(msg, *args, **kw)
        elif self.loglevel <= logging.INFO: print_info(msg, *args)
    def debug(self, msg, *args, **kw):
        if self.logenabled: logging.debug(msg, *args, **kw)
        elif self.loglevel <= logging.DEBUG: print_debug(msg, *args)
    def trace(self, msg, *args, **kw):
        if self.logenabled: logging.log(TRACE, msg, *args, **kw)
        elif self.loglevel <= TRACE: print_trace(msg, *args)

    @classmethod
    def parse_args(cls, default_config=None, args=None):
        from optparse import OptionParser, OptionGroup
        OP = OptionParser(usage=u"\n\t%prog")
        OP.add_option('-L', '--logfile', dest='logfile',
                      help=u"Spécifier l'emplacement du fichier de logs.")
        OP.add_option('-d', '--loglevel', dest='loglevel',
                      help=u"Spécifier le niveau de logs qui sont enregistrés (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)")
        OP.add_option('--pidfile', dest='pidfile',
                      help=u"Spécifier l'emplacement du fichier de pid.")
        OP.add_option('-s', '--socket-path', dest='socket_path',
                      help=u"Spécifier l'emplacement du fichier de socket.")
        OP.add_option('--socket-owner', dest='socket_owner',
                      help=u"Spécifier le propriétaire du fichier de socket.")
        OP.add_option('--socket-mode', dest='socket_mode',
                      help=u"Spécifier le mode du fichier de socket.")
        OP.add_option('-c', '--config', dest='config',
                      help=u"Spécifier le fichier de configuration. Par défaut prendre le fichier de même nom de base que ce script avec l'extension .rules")
        OP.add_option('-v', '--var', action='append', dest='vars', metavar='NAME=VALUE',
                      help=u"(Re)définir une variable")
        OG = OptionGroup(OP, u"Options de connexion")
        OG.add_option('-H', '--ldapuri', dest='ldapuri',
                      help=u"LDAP URI of the server")
        OG.add_option('-x', '--simpleauth', action='store_true', dest='simpleauth',
                      help=u"Use simple authentication")
        OG.add_option('-D', '--binddn', dest='binddn',
                      help=u"Bind DN for simple authentication")
        OG.add_option('-w', '--password', dest='credentials',
                      help=u"Credentials")
        OG.add_option('-Y', '--saslmech', dest='saslmech',
                      help=u"SASL mechanism")
        OG.add_option('-U','--authcid',  dest='authcid',
                      help=u"SASL authentication identity")
        OG.add_option('-X', '--authzid', dest='authzid',
                      help=u"SASL authorization identity")
        OG.add_option('-R', '--realm', dest='realm',
                      help=u"SASL realm")
        OP.add_option_group(OG)
        OG = OptionGroup(OP, u"Options avancées")
        OG.add_option('--logformat', dest='logformat',
                      help=u"Spécifier le format des lignes de logs.")
        OG.add_option('--devel', action='store_true', dest='devel',
                      help=u"Activer le mode développement: les données sont lues sur STDIN, le résultat affiché sur STDOUT, et les logs sur STDERR. En mode développement, les options --logfile, --socket-path, --socket-owner sont ignorées")
        OG.add_option('--devel-input', dest='input',
                      help=u"En mode développement, lire les données depuis le fichier spécifié")
        OG.add_option('--devel-output', dest='output',
                      help=u"En mode développement, écrire les données dans le fichier spécifié")
        OG.add_option('--devel-ldif-output', dest='devel_ldif_output', metavar='LDIF-OUTPUT',
                      help=u"En mode développement, écrire les données au format LDIF dans le fichier spécifié au lieu de mettre à jour le serveur LDAP")
        OG.add_option('--run-state', dest='action', metavar='STATE',
                      help=u"Lancer le traitement correspondant à l'état spécifié.")
        OG.add_option('--no-init', action='store_true', dest='no_init',
                      help=u"Désactiver le traitement de l'état 'init'. A utiliser avec --run-state pour être sûr de ne lancer que les actions de l'état spécifié.")
        OP.add_option_group(OG)
        o, args = OP.parse_args(args)

        inf = None
        if o.input is not None: inf = open(o.input, 'rb')
        outf = None
        if o.output is not None: out = open(o.output, 'wb')

        env = cls(inf, outf)
        env.devel = o.devel
        env.devel_ldif_output = o.devel_ldif_output
        env.action = validate_state(o.action, True)
        env.load_config(o.config, default_config)
        if o.logfile is not None: env.logfile = validate_logfile(o.logfile)
        if o.loglevel is not None: env.loglevel = validate_loglevel(o.loglevel)
        if o.logformat is not None: env.logformat = o.logformat
        if o.pidfile is not None: env.pidfile = o.pidfile
        if o.socket_path is not None: env.socket_path = o.socket_path
        if o.socket_owner is not None: env.socket_owner = o.socket_owner
        if o.socket_mode is not None: env.socket_mode = o.socket_mode
        if o.ldapuri or o.simpleauth or o.binddn or o.credentials \
                or o.saslmech or o.authcid or o.authzid or o.realm:
            env.server = validate_server(
                None, ldapuri=o.ldapuri, simpleauth=o.simpleauth, binddn=o.binddn,
                saslmech=o.saslmech, authcid=o.authcid, authzid=o.authzid, realm=o.realm,
                credentials=o.credentials)
        if o.vars is not None:
            for var in o.vars:
                env.set_var(clvar=var)
        env.configure_logging()
        env.debug_dump_rules()

        if env.devel_ldif_output: worker = LDIFOutput(env.devel_ldif_output)
        else: worker = LDAPWorker(env.server)
        worker.init_rules(env.rules)
        env.worker = worker

        if not o.no_init: env.set_state('init')
        return env

    def __init__(self, inf=None, outf=None):
        if inf is None: inf = sys.stdin
        if outf is None: outf = sys.stdout
        self.inf = inf
        self.outf = outf

    RE_CLVAR = re.compile(r'(\w+)(?:\s*=\s*(.*)\s*)?$')
    def set_var(self, name=None, value=None, mo=None, clvar=None):
        if mo is None:
            mo = self.RE_CLVAR.match(clvar)
        if name is None:
            name = mo.group(1)
            value = mo.group(2) or ''
        self.vars[name] = value

    def set_state(self, state):
        self.state = state
        self.apply_rules()

    def configure_logging(self):
        logfile = self.logfile if not self.devel else None
        init_log(logfile, self.loglevel, self.logformat)

    RE_IGNORE = re.compile(r'\s*(?:#.*)?$')
    RE_VAR = re.compile(r'var\s+(\w+)(?:\s+(.*)\s*)?$')
    CONF_PATTERNS = (
        ('logfile', re.compile(r'logfile\s+(.+)'), validate_logfile),
        ('loglevel', re.compile(r'loglevel\s+(.+)'), validate_loglevel),
        ('logformat', re.compile(r'logformat\s+(.+)')),
        ('pidfile', re.compile(r'pidfile\s+(.+)')),
        ('socket_path', re.compile(r'socket(?:_path)?\s+(.+)')),
        ('socket_owner', re.compile(r'socket_owner\s+(.+)')),
        ('socket_mode', re.compile(r'socket_mode\s+(.+)')),
        ('server', re.compile(r'server\s+(.+)'), validate_server),
        )
    def load_config(self, config, default_configs=None):
        self.vars = {}
        self.rules = []
        self.server = validate_server()
        if config is None and default_configs is not None:
            if not isseq(default_configs): default_configs = [default_configs]
            for default_config in default_configs:
                if path.exists(default_config):
                    config = default_config
                    break
        if config is not None:
            inf = open(config, 'rb')
            # Analyser les directives
            mark = None
            while True:
                mark = inf.tell()
                line = inf.readline()
                if line == '': break
                line = line.strip()
                mo = self.RE_IGNORE.match(line)
                if mo is not None: continue
                mo = self.RE_VAR.match(line)
                if mo is not None:
                    self.set_var(mo=mo)
                    continue
                valid_conf = False
                for npv in self.CONF_PATTERNS:
                    name, pattern = npv[:2]
                    validator = npv[2] if npv[2:3] else None
                    mo = pattern.match(line)
                    if mo is not None:
                        value = mo.group(1)
                        if validator is not None: value = validator(value)
                        setattr(self, name, value)
                        valid_conf = True
                        break
                if valid_conf: continue
                inf.seek(mark)
                break
            # Analyser les règles
            RulesParser(inf).parse_rules(self)
            inf.close()

    def debug_dump_rules(self):
        count = 0
        for rule in self.rules:
            self.debug('Rule #%i is:\n%s' % (count, str(rule)))
            count += 1

    def before_start(self, handler=None):
        self.set_state('before_start')
        if self.devel:
            self.socket_path = None
            self.socket_owner = None
            self.socket_mode = None
            self.pidfile = None
        elif self.socket_path is None:
            raise ValueError("socket_path is required")

        signal(SIGTERM, getsignal(SIGINT))
        atexit.register(self.before_stop)
        if self.pidfile is not None:
            dir = path.dirname(self.pidfile)
            if dir and not path.isdir(dir):
                logging.info("Creating pidfile dir %s", dir)
                os.makedirs(dir)
            pid = str(os.getpid())
            logging.debug("Running with PID %s", pid)
            outf = open(self.pidfile, 'wb')
            outf.write(pid)
            outf.close()
        if self.socket_path is not None:
            dir = path.dirname(self.socket_path)
            if dir and not path.isdir(dir):
                logging.info("Creating socket_path dir %s", dir)
                os.makedirs(dir)
            if path.exists(self.socket_path):
                os.unlink(self.socket_path)
        if handler is not None:
            handler.set_env(self)
        self.worker.before_start()

    def after_start(self):
        if self.socket_path is not None:
            if self.socket_owner is not None: chown(self.socket_path, self.socket_owner)
            if self.socket_mode is not None: chmod(self.socket_path, self.socket_mode)
        self.worker.after_start()
        self.set_state('after_start')

    def before_stop(self):
        self.set_state('before_stop')
        self.worker.before_stop()
        if self.socket_path is not None and path.exists(self.socket_path):
            try: os.unlink(self.socket_path)
            except: pass
        if self.pidfile is not None and path.exists(self.pidfile):
            try: os.unlink(self.pidfile)
            except: pass
        logging.shutdown()

    def apply_rules(self, idata=None):
        if idata is None: idata = {}
        for name, value in self.vars.items():
            # don't allow variables to overwrite existing values
            idata.setdefault(name, value)
        idata.update(state=self.state,
                     logfile=self.logfile, loglevel=self.loglevel, logformat=self.logformat,
                     socket_path=self.socket_path, socket_owner=self.socket_owner)
        self.trace("apply_rules for idata=%r", idata)
        self.worker.apply_rules(idata)
