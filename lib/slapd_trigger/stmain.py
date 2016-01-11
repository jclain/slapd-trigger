# -*- coding: utf-8 mode: python -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8

__all__ = (
    'BacksockParser', 'DebugHandler', 'SocketHandler',
    'run_slapd_trigger',
    )

import logging
from os import path
from SocketServer import UnixStreamServer, StreamRequestHandler
try: from cStringIO import StringIO
except: from StringIO import StringIO

from stldif import *
from stenv import *

class BacksockParser(LDIFParser):
    """back-sock data parser
    """
    handler = None
    env = None

    operation = None
    params = None
    changetype = None
    data = None

    def __next_line(self, lines, until=None):
        if not lines: return ''
        olines, ilines = [lines[0]], lines[1:]
        while ilines and ilines[0][0] == ' ':
            olines.append(ilines[0][1:])
            ilines = ilines[1:]
        line = ''.join(olines)
        if until is not None:
            mo = parse_ldif_line(line, until)
            if mo is not None: return None
        lines[:] = ilines
        return line

    def __parse_data(self, inf):
        lines = []
        while not self.EOF:
            line = self._readline1(inf)
            if not line or self.EOF: break
            lines.append(line)
        if not lines: raise EOFError()
        self.env.trace("BacksockParser got data:\n%s", '\n'.join(lines))

        self.operation = self.__next_line(lines)
        while True:
            line = self.__next_line(lines, 'dn')
            if line is None: break
            if self.params is None: self.params = {}
            name, value = parse_ldif_line(line)
            params = self.params
            if params.has_key(name):
                if not isseq(params[name]): params[name] = [params[name]]
                params[name].append(value)
            else:
                params[name] = value
        self.data = '\n'.join(lines)

    def __init__(self, handler):
        self.handler = handler
        self.env = handler.env
        self.__parse_data(handler)
        LDIFParser.__init__(self, StringIO(self.data))

    def process_data(self):
        try:
            if not self.operation: raise ValueError("operation line not provided")
            if not self.params: raise ValueError("msgid: and suffix: lines missing")
            if not self.data: raise ValueError("not enough data")

            if self.operation == 'MODIFY':
                self.changetype = 'modify'
                self.parse_change_records()
            elif self.operation == 'MODRDN':
                self.changetype = 'modrdn'
                self.parse_entry_records()
            elif self.operation == 'ADD':
                self.changetype = 'add'
                self.parse_entry_records()
            elif self.operation == 'DELETE':
                self.changetype = 'delete'
                self.parse_entry_records()
            else:
                logging.error("%s: Unsupported operation" % self.operation)
                return False
            return True
        except:
            logging.exception("process_data")
            return False
        finally:
            self.handler.write("CONTINUE")

    def get_idata(self, **kw):
        idata = dict(operation=self.operation)
        idata.update(self.params)
        idata.update(kw)
        return idata

    def handle(self, dn, entry):
        idata = self.get_idata(dn=dn, changetype=self.changetype, entry=entry)
        self.env.apply_rules(idata)

    def handle_modify(self, dn, modops, controls=None):
        idata = self.get_idata(dn=dn, changetype=self.changetype, mod_controls=controls, mod_ops=modops)
        self.env.apply_rules(idata)

class DebugHandler:
    env = None
    @classmethod
    def set_env(cls, env): cls.env = env

    def readline(self): return self.env.inf.readline()
    def write(self, data): self.env.outf.write(data)

    def start(self):
        self.env.after_start()
        while True:
            try: BacksockParser(self).process_data()
            except EOFError: break

class SocketHandler(StreamRequestHandler):
    env = None
    @classmethod
    def set_env(cls, env): cls.env = env

    def readline(self): return self.rfile.readline()
    def write(self, data): self.wfile.write(data)

    def handle(self):
        BacksockParser(self).process_data()

def run_slapd_trigger(script=None):
    if script is None: script = __file__
    scriptdir, scriptname = path.split(script)
    rulesname = '%s.rules' % path.splitext(scriptname)[0]
    env = Env.parse_args([path.join(scriptdir, rulesname),
                          path.join("/etc/ldap", rulesname)])
    if env.action:
        env.set_state(env.action)
    elif env.devel:
        env.before_start(DebugHandler)
        DebugHandler().start()
    else:
        env.before_start(SocketHandler)
        logging.info("Listening on %s", env.socket_path)
        server = UnixStreamServer(env.socket_path, SocketHandler)
        env.after_start()
        server.serve_forever()
