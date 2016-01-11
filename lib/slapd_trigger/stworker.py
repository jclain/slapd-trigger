# -*- coding: utf-8 mode: python -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8

__all__ = (
    'LDIFOutput',
    'LDAPWorker',
    )

import sys, logging
from collections import deque
from threading import Thread, Condition, Event

from stutil import *
from stldif import LDIFWriter

class AbstractWorker:
    rules = None

    def init_rules(self, rules):
        self.rules = rules[:]

    def before_start(self): pass
    def after_start(self): pass
    def before_stop(self): pass

    def read(self, dn, attrs=None): return None
    def write(self, modifs, infos=None): pass
    def apply_rules(self, idata=None):
        count = 0
        modifs = []
        for rule in self.rules:
            matches = rule.match(idata)
            log_trace("rule #%i, matches=%r", count, matches)
            if matches is not False:
                odata = rule.get_odata(idata, matches)
                #XXX merge odata in modifs
                modifs.append(odata)
            count += 1
        log_trace("result modifs=%r\n", modifs)
        if modifs: self.write(modifs)

class LDIFOutput(AbstractWorker):
    outf = None
    close = None

    def __init__(self, outf=None):
        if outf in (None, '-', '/dev/stdout'):
            outf = sys.stdout
            close = False
        elif outf == '/dev/stderr':
            outf = sys.stderr
            close = False
        else:
            outf = open(outf, 'ab')
            close = True
        self.outf = outf
        self.close = close

    def write(self, modifs, infos=None):
        if infos is not None:
            for line in infos.split('\n'):
                outf.write("# ")
                outf.write(line)
                outf.write("\n")
        w = LDIFWriter(self.outf)
        for modif in modifs:
            dn = modif[0]
            changetype = modif[1]
            if changetype in ('modify', 'add'):
                data = modif[2]
                if data:
                    w.unparse(dn, data)
                else:
                    w._unparseAttrTypeandValue('dn', dn)
                    w._unparseAttrTypeandValue('changetype', changetype)
                    w._output_file.write(w._line_sep)
                    w.records_written += 1
            elif changetype == 'modrdn':
                data = modif[2] or []
                w._unparseAttrTypeandValue('dn', dn)
                w._unparseAttrTypeandValue('changetype', changetype)
                for attr, values in data:
                    for value in values:
                        w._unparseAttrTypeandValue(attr, value)
                w._output_file.write(w._line_sep)
                w.records_written += 1
            elif changetype == 'delete':
                w._unparseAttrTypeandValue('dn', dn)
                w._unparseAttrTypeandValue('changetype', changetype)
                w._output_file.write(w._line_sep)
                w.records_written += 1
            else:
                raise ValueError("Unexpected changetype: %r" % changetype)

    def before_stop(self):
        if self.close:
            self.outf.close()
            self.outf = None

class LDAPWorker(AbstractWorker, Thread):
    ldapuri = None
    simpleauth = None
    binddn = None
    saslmech = None
    authcid = None
    authzid = None
    realm = None
    credentials = None

    event = None
    should_stop = None
    queue = None
    conn = None

    def __init__(self, config):
        self.ldapuri = config['ldapuri']
        self.simpleauth = config['simpleauth']
        if self.simpleauth:
            self.binddn = config.get('binddn', None)
        else:
            self.saslmech = config['saslmech']
            self.authcid = config.get('authcid', None)
            self.authzid = config.get('authzid', None)
            self.realm = config.get('realm', None)
        self.credentials = config.get('credentials', None)
        self.event = Condition()
        self.should_stop = Event()
        self.queue = deque()
        Thread.__init__(self, name='stworker')
        self.daemon = True

    def get_conn(self):
        conn = self.conn
        if conn is None:
            import ldap; from ldap import sasl
            conn = ldap.initialize(self.ldapuri)
            conn.set_option(ldap.OPT_PROTOCOL_VERSION, ldap.VERSION3)
            if self.simpleauth:
                conn.simple_bind_s(self.binddn, self.credentials)
            else:
                saslmech = self.saslmech.lower()
                if saslmech == 'cram-md5':
                    auth = sasl.cram_md5(self.authcid, self.credentials, self.authzid)
                elif saslmech == 'digest-md5':
                    auth = sasl.digest_md5(self.authcid, self.credentials, self.authzid)
                elif saslmech == 'gssapi':
                    auth = sasl.gssapi(self.authzid)
                elif saslmech == 'external':
                    auth = sasl.external(self.authzid)
                conn.sasl_interactive_bind_s('', auth)
            self.conn = conn
        return conn

    def before_start(self):
        self.start()
    def before_stop(self):
        self.event.acquire()
        self.should_stop.set()
        self.event.notify()
        self.event.release()
        self.join()
        if self.conn is not None:
            try: self.conn.unbind_s()
            finally: self.conn = None

    def read(self, dn, attrs=None):
        pass #conn = self.get_conn()

    def write(self, modifs, infos=None):
        self.event.acquire()
        self.queue.append(modifs)
        self.event.notify()
        self.event.release()

    def run(self):
        while not self.should_stop.is_set():
            log_trace("Waiting for event...")
            self.event.acquire()
            self.event.wait()
            self.event.release()
            if self.should_stop.is_set(): break
            while not self.should_stop.is_set():
                try: modifs = self.queue.pop()
                except IndexError: break
                logging.debug("Worker got %r", modifs)
                for modif in modifs:
                    conn = self.get_conn()
                    dn = modif[0]
                    changetype = modif[1]
                    if changetype == 'modify':
                        conn.modify_s(dn, modif[2])
                    elif changetype == 'modrdn':
                        entry = dict(modif[2])
                        newrdn = entry['newrdn']
                        newsup = entry.get('newsuperior', None)
                        delold = entry.get('deleteoldrdn', 1)
                        conn.rename_s(newrdn, newsup, delold)
                    elif changetype == 'add':
                        conn.add_s(dn, modif[2])
                        pass
                    elif changetype == 'delete':
                        conn.delete_s(dn)
        log_trace("Stopping...")
