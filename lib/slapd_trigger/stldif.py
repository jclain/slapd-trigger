# -*- coding: utf-8 mode: python -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8

__all__ = (
    'LDIFWriter',
    'LDIFParser', 'CHANGE_TYPES', 'is_dn',
    'MOD_ADD', 'MOD_DELETE', 'MOD_REPLACE', 'MATCH_MOD_MODIFY', 'MATCH_MOD_ANY',
    'MOD_OP_INTEGER', 'MOD_OP_STR',
    'MATCH_MOD_OP_INTEGER', 'MATCH_MOD_OP_STR',
    'LDIFLineParser', 'parse_ldif_line',
    )

try: from cStringIO import StringIO
except: from StringIO import StringIO

from ldif import LDIFWriter
from ldif import LDIFParser as pyldap_LDIFParser
from ldif import CHANGE_TYPES, MOD_OP_INTEGER, MOD_OP_STR, is_dn

MOD_ADD = 0
MOD_DELETE = 1
MOD_REPLACE = 2
MATCH_MOD_MODIFY = 98
MATCH_MOD_ANY = 99
MATCH_MOD_OP_INTEGER = {
    'add': MOD_ADD, 'delete': MOD_DELETE, 'replace': MOD_REPLACE,
    # for the match-OP attribute, special values
    # - 'modify' has the meaning 'add' OR 'replace'
    # - 'any' has the meaning 'add' OR 'replace' OR 'delete'
    'modify': MATCH_MOD_MODIFY, 'any': MATCH_MOD_ANY,
    }
MATCH_MOD_OP_STR = {}
for k, v in MATCH_MOD_OP_INTEGER.items(): MATCH_MOD_OP_STR[v] = k

class LDIFParser(pyldap_LDIFParser):
    # Like the original, but _readline() can detect EOF condition
    EOF = None
    def _readline1(self, inf):
        s = inf.readline()
        if s == '': self.EOF = True
        if s[-2:] == '\r\n': return s[:-2]
        elif s[-1:] == '\n': return s[:-1]
        else: return s
    def _readline(self):
        s = self._input_file.readline()
        if s == '': self.EOF = True
        self.line_counter = self.line_counter + 1
        self.byte_counter = self.byte_counter + len(s)
        if s[-2:] == '\r\n': return s[:-2]
        elif s[-1:] == '\n': return s[:-1]
        else: return s

class LDIFLineParser(LDIFParser):
    """Single 'attr: value' line parser
    """
    name = None
    value = None

    def __init__(self, line):
        LDIFParser.__init__(self, StringIO(line))
        self.name, self.value = self._next_key_and_value()

def parse_ldif_line(line, name=None):
    """Given line=='attr: value'
    If name is None, return ('attr', 'value')
    If name is not None, return 'value' if name=='attr'
    """
    llp = LDIFLineParser(line)
    if name is None: return llp.name, llp.value
    elif llp.name == name: return llp.value
    else: return None
