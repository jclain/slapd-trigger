# -*- coding: utf-8 mode: python -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8

__all__ = (
    'RulesParser', 'Rule',
    'validate_state',
    )

import re, logging

from stutil import *
from stldif import *

STATE_ALIAS_MAP = {'start': 'before_start', 'started': 'after_start', 'stop': 'before_stop'}
VALID_STATES = ('setup', 'init', 'before_start', 'after_start', 'before_stop')
ACTION_STATES = ('setup', 'before_start', 'before_stop')
def validate_state(state, action_only=False):
    if state is None: return None
    orig_state = state
    state = STATE_ALIAS_MAP.get(state, state)
    valid_states = VALID_STATES if not action_only else ACTION_STATES
    if state not in valid_states:
        raise ValueError("Invalid state: %r" % orig_state)
    return state

class RulesParser(LDIFParser):
    """Rules parser
    """

    def __init__(self, inf):
        LDIFParser.__init__(self, inf)

    RE_MATCH_DN = re.compile(r'match-dn(?:\.(\w+))?$')
    RE_MATCH_VAR = re.compile(r'match-(state|operation|msgid|suffix|binddn|peername|ssf|connid|changetype)$')
    RE_MATCH_OP = re.compile(r'match-(add|replace|delete|modify|any)$')
    RE_MATCH_ATTR = re.compile(r'(.+)(?:\.(exact|regex))?$')
    # attribut qui fait passer à l'analyse des lignes d'opération
    RE_OP = re.compile(r'(dn|changetype|add|delete|replace)$')

    DNSTYLE_ALIAS_MAP = {'base': 'baseobject', 'one': 'onelevel', 'sub': 'subtree'}
    VALID_DNSTYLES = ('exact', 'baseobject', 'regex', 'onelevel', 'subtree', 'children')
    DEFAULT_DNSTYLE = 'subtree'
    def validate_dnstyle(self, dnstyle):
        orig_dnstyle = dnstyle
        if dnstyle is None: dnstyle = self.DEFAULT_DNSTYLE
        dnstyle = self.DNSTYLE_ALIAS_MAP.get(dnstyle, dnstyle)
        if dnstyle not in self.VALID_DNSTYLES:
            raise ValueError("Invalid dnstyle: %r" % orig_dnstyle)
        return dnstyle

    VALTYPE_ALIAS_MAP = {}
    VALID_VALTYPES = ('exact', 'regex')
    DEFAULT_VALTYPE = 'regex'
    def validate_valtype(self, valtype):
        orig_valtype = valtype
        if valtype is None: valtype = self.DEFAULT_VALTYPE
        valtype = self.VALTYPE_ALIAS_MAP.get(valtype, valtype)
        if valtype not in self.VALID_VALTYPES:
            raise ValueError("Invalid valtype: %r" % orig_valtype)
        return valtype

    def parse_rules(self, env):
        k, v = self._next_key_and_value() #;env.trace("00 got k=%r, v=%r", k, v)
        while True:
            # skip separator lines
            if k is None:
                if self.EOF: break
                k, v = self._next_key_and_value() #;env.trace("01 got k=%r, v=%r", k, v)
                continue

            match_vars = []
            match_dns = []
            match_ops = []
            dn = None
            changetype = 'modify'
            mod_controls = []
            mod_ops = []
            entry = {}

            # first, parse match lines
            while True:
                if k is None: break
                if self.RE_OP.match(k) is not None: break

                mo = self.RE_MATCH_VAR.match(k)
                if mo is not None:
                    name = mo.group(1)
                    if name == 'state': v = validate_state(v)
                    elif name == 'changetype' and not v in CHANGE_TYPES: raise ValueError('Invalid changetype: %r' % v)
                    match_vars.append((name, v))
                    k, v = self._next_key_and_value() #;env.trace("02 got k=%r, v=%r", k, v)
                    continue

                mo = self.RE_MATCH_DN.match(k)
                if mo is not None:
                    dnstyle = self.validate_dnstyle(mo.group(1))
                    match_dns.append((dnstyle, v))
                    k, v = self._next_key_and_value() #;env.trace("03 got k=%r, v=%r", k, v)
                    continue

                mo = self.RE_MATCH_OP.match(k)
                if mo is not None:
                    try: match_op = MATCH_MOD_OP_INTEGER[mo.group(1)]
                    except KeyError: raise ValueError('Line %d: Invalid mod-op string: %r' % (self.line_counter, k))
                    match_attr = v
                    match_values = []
                    k, v = self._next_key_and_value() #;env.trace("04 got k=%r, v=%r", k, v)
                    while True:
                        if k is None: break
                        if k == '-':
                            k, v = self._next_key_and_value() #;env.trace("05 got k=%r, v=%r", k, v)
                            break
                        mo = self.RE_MATCH_ATTR.match(k)
                        if mo is None: break # should not happen
                        attr = mo.group(1)
                        valtype = self.validate_valtype(mo.group(2))
                        if attr != match_attr: break
                        match_values.append((valtype, v))
                        k, v = self._next_key_and_value() #;env.trace("06 got k=%r, v=%r", k, v)
                    match_ops.append((match_op, match_attr, match_values or None))

            # then, parse op lines
            if k == 'dn':
                if not is_dn(v):
                    raise ValueError('Line %d: Not a valid string-representation for dn: %r' % (self.line_counter, v))
                dn = v
                k, v = self._next_key_and_value() #;env.trace("07 got k=%r, v=%r", k, v)

            while k == 'control':
                try:
                    control_type, criticality, control_value = v.split(' ', 2)
                except ValueError:
                    control_value = None
                    control_type, criticality = v.split(' ', 1)
                mod_controls.append((control_type, criticality, control_value))
                k, v = self._next_key_and_value() #;env.trace("08 got k=%r, v=%r", k, v)

            if k == 'changetype':
                if not v in CHANGE_TYPES: raise ValueError('Invalid changetype: %r' % v)
                changetype = v
                k, v = self._next_key_and_value() #;env.trace("09 got k=%r, v=%r", k, v)

            if changetype == 'modify':
                while k != None:
                    try: modop = MOD_OP_INTEGER[k]
                    except KeyError: raise ValueError('Line %d: Invalid mod-op string: %r' % (self.line_counter, k))
                    modattr = v
                    modvalues = []
                    k, v = self._next_key_and_value() #;env.trace("10 got k=%r, v=%r", k, v)
                    while k == modattr:
                        modvalues.append(v)
                        k, v = self._next_key_and_value() #;env.trace("11 got k=%r, v=%r", k, v)
                    mod_ops.append((modop, modattr, modvalues or None))
                    if k == '-':
                        k, v = self._next_key_and_value() #;env.trace("12 got k=%r, v=%r", k, v)
            elif changetype == 'add':
                attrs = []
                while k != None:
                    if k not in attrs: attrs.append(k)
                    if not entry.has_key(k): entry[k] = []
                    entry[k].append(v)
                    k, v = self._next_key_and_value() #;env.trace("13 got k=%r, v=%r", k, v)
                for key in attrs:
                    mod_ops.append((key, entry[key]))
                entry = None
            else:
                while k != None:
                    if not entry.has_key(k): entry[k] = []
                    entry[k].append(v)
                    k, v = self._next_key_and_value() #;env.trace("14 got k=%r, v=%r", k, v)

            matches = dict(vars=match_vars or None,
                           dns=match_dns or None,
                           ops=match_ops or None)
            odata = dict(dn=dn or None,
                         changetype=changetype or None,
                         mod_ops=mod_ops or None,
                         mod_controls=mod_controls or None,
                         entry=entry or None)
            env.rules.append(Rule(matches, odata))

class Rule:
    matches = None
    odata = None

    def __init__(self, matches, odata):
        self.matches = matches
        self.odata = odata

    RE_MATCH = re.compile(r'(?<!\\)\\(?:([1-9][0-9]?)|g<(\d+|\w+)>)')
    def replace_matches(self, value, matches):
        if value is None: return None
        elif isseq(value): return [self.replace_matches(v, matches) for v in value]
        result = []
        parts = self.RE_MATCH.split(value)
        i = 0
        while i + 3 < len(parts):
            result.append(parts[i])
            key = parts[i + 1]
            if key is None: key = parts[i + 2]
            result.append(matches.get(key, ''))
            i += 3
        result.append(parts[i])
        return ''.join(result)

    RE_VAR = re.compile(r'(\\*)\$\{(\w+)\}')
    def replace_vars(self, value, idata):
        if value is None: return None
        elif isseq(value): return [self.replace_vars(v, idata) for v in value]
        result = []
        parts = self.RE_VAR.split(value)
        i = 0
        while i + 3 < len(parts):
            result.append(parts[i])
            prefix = parts[i + 1] or ''
            name = parts[i + 2]
            plen = len(prefix)
            if plen % 2 == 0:
                prefix = (plen / 2) * '\\'
                result.append(prefix)
                result.append(idata.get(name, ''))
            else:
                prefix = prefix[:-1]
                result.append(prefix)
                result.append('${')
                result.append(name)
                result.append('}')
            i += 3
        result.append(parts[i])
        return ''.join(result)

    def replace(self, value, matches, idata):
        if value is not None:
            value = self.replace_matches(value, matches)
            value = self.replace_vars(value, idata)
        return value

    def match_attr(self, expected, attr):
        if expected is None: return True # no match is required
        elif attr is None: return False # no value was provided
        elif isseq(attr): return filter(None, [self.match_attr(expected, a) for a in attr])
        # compare ignoring case
        if isseq(expected):
            return attr.lower() in [xattr.lower() for xattr in expected]
        else:
            return attr.lower() == expected.lower()

    def match_regex(self, expected, value):
        if expected is None: return True # no match is required
        elif value is None: return False # no value was provided
        elif isseq(value): return filter(None, [self.match_regex(expected, v) for v in value])
        if not isseq(expected): expected = [expected]
        for xpattern in expected:
            mo = re.match(xpattern, value)
            if mo is not None: return mo
        return False

    def match_value(self, expected, value, valtype='exact'):
        if expected is None: return True # no match is required
        elif value is None: return False # no value was provided
        elif isseq(value): return filter(None, [self.match_value(expected, v, valtype) for v in value])
        if isseq(expected):
            if valtype == 'exact':
                return value in expected
            elif valtype == 'regex':
                return self.match_regex(expected, value)
        else:
            if valtype == 'exact':
                return value == expected
            elif valtype == 'regex':
                return self.match_regex(expected, value)
        raise ValueError("Unexpected valtype %r" % valtype)

    def match_dn(self, expected, dn, dnstyle):
        if expected is None: return True # no match is required
        elif dn is None: return False # no value was provided
        elif isseq(dn): return filter(None, [self.match_dn(expected, d, dnstyle) for d in dn])
        # compare ignoring case
        dn = dn.lower()
        if isseq(expected):
            expected = [xdn.lower() for xdn in expected]
            if dnstyle == 'exact' or dnstyle == 'baseobject':
                return dn in expected
            elif dnstyle == 'regex':
                return self.match_regex(expected, dn)
            suffixes = [',%s' % xdn for xdn in expected]
            if dnstyle == 'onelevel':
                for suffix in suffixes:
                    if dn.endswith(suffix):
                        rdn = dn[:-len(suffix)]
                        if rdn.count(',') == 0: return True
                return False
            elif dnstyle == 'subtree':
                if dn in expected: return True
                for suffix in suffixes:
                    if dn.endswith(suffix): return True
                return False
            elif dnstyle == 'children':
                for suffix in suffixes:
                    if dn.endswith(suffix): return True
                return False
        else:
            expected = expected.lower()
            if dnstyle == 'exact' or dnstyle == 'baseobject':
                return dn == expected
            elif dnstyle == 'regex':
                return self.match_regex(expected, dn)
            suffix = ',%s' % expected
            if dnstyle == 'onelevel':
                if not dn.endswith(suffix): return False
                rdn = dn[:-len(suffix)]
                return rdn.count(',') == 0
            elif dnstyle == 'subtree':
                return dn == expected or dn.endswith(suffix)
            elif dnstyle == 'children':
                return dn.endswith(suffix)
        raise ValueError("Unexpected dnstyle %r" % dnstyle)

    def update_matches(self, matches, mcount, mo):
        if mo is None or mo is False or mo is True: return mcount
        if not isseq(mo): mos = [mo]
        else: mos = mo
        for mo in mos:
            for group in mo.groups():
                mcount += 1
                matches[str(mcount)] = group
            for name, group in mo.groupdict().items():
                matches[name] = group
        return mcount

    def match(self, idata):
        matches = {}
        mcount = 0

        xvars = self.matches['vars']
        if xvars is not None:
            for name, xvalue in xvars:
                xvalue = self.replace_vars(xvalue, idata)
                value = idata.get(name, None)
                if not self.match_value(xvalue, value):
                    return False
        xdns = self.matches['dns']
        if xdns is not None:
            dn = idata.get('dn', None)
            for dnstyle, xdn in xdns:
                xdn = self.replace_vars(xdn, idata)
                mo = self.match_dn(xdn, dn, dnstyle)
                if mo is False: return False
                mcount = self.update_matches(matches, mcount, mo)
        xops = self.matches['ops']
        if xops is not None:
            for xop, xattr, xvalues in xops:
                match_op = False
                ops = idata.get('mod_ops', None)
                entry = idata.get('entry', None)
                values = None
                # verify op AND get corresponding values
                if values is None and ops is not None:
                    for op, attr, ivalues in ops:
                        if not self.match_attr(xattr, attr): continue
                        if xop == MATCH_MOD_MODIFY and op in (MOD_ADD, MOD_REPLACE): match_op = True
                        elif xop == MATCH_MOD_ANY: match_op = True
                        elif xop == op: match_op = True
                        if match_op:
                            values = ivalues
                            break
                if values is None and entry is not None:
                    changetype = idata.get('changetype', None)
                    # XXX à valider en condition réelles...
                    # par exemple, peut-on avoir match-delete: attr qui correspond à une opération DELETE?
                    for attr, ivalues in entry.items():
                        if not self.match_attr(xattr, attr): continue
                        if xop == MATCH_MOD_MODIFY and changetype in ('modify', 'modrdn', 'add'): match_op = True
                        elif xop == MATCH_MOD_ANY: match_op = True
                        elif xop == MOD_ADD and changetype == 'add': match_op = True
                        elif xop == MOD_DELETE and changetype == 'delete': match_op = True
                        if match_op:
                            values = ivalues
                            break
                if match_op and xvalues is None: continue
                elif xvalues is None: return False
                elif values is None: return False
                # once we have op match, check values
                match_value = False
                for valtype, xvalue in xvalues:
                    for value in values:
                        mo = self.match_value(xvalue, value, valtype)
                        if mo is False: continue
                        match_value = True
                        mcount = self.update_matches(matches, mcount, mo)
                if not match_value: return False

        return matches

    def get_odata(self, idata, matches):
        odata = self.odata
        dn = odata.get('dn', None)
        changetype = odata.get('changetype', None)
        if dn is None: dn = idata.get('dn', None)
        if dn is None: raise ValueError("dn: is required") #should not happen

        result = [dn, changetype]
        if changetype == 'modify':
            modops = odata.get('mod_ops', [])
            controls = odata.get('mod_controls', None)
            result.append([(modop, modattr, self.replace(modvalues, matches, idata))
                           for modop, modattr, modvalues in modops])
            result.append(controls)
        elif changetype == 'modrdn':
            entry = odata.get('entry', {})
            result.append([(entattr, self.replace(entvalues, matches, idata))
                           for entattr, entvalues in entry.items()])
        elif changetype == 'add':
            additems = odata.get('mod_ops', [])
            result.append([(addattr, self.replace(addvalues, matches, idata))
                           for addattr, addvalues in additems])
        elif changetype == 'delete':
            pass
        else:
            raise ValueError("Unexpected changetype: %r" % changetype)
        return result

    def __str__(self):
        # pretty prints the rule
        mlines = []
        vars = self.matches['vars']
        if vars is not None:
            terms = ['%s %s' % (name, value) for name, value in vars]
            mlines.append('\nAND '.join(terms))
        dns = self.matches['dns']
        if dns is not None:
            terms = ['dn.%s=%r' % (dnstyle, dn) for dnstyle, dn in dns]
            mlines.append('\nAND '.join(terms))
        ops = self.matches['ops']
        if ops is not None:
            terms = []
            for op, attr, values in ops:
                if values is None:
                    terms.append('%s %s' % (MATCH_MOD_OP_STR[op], attr))
                else:
                    for valtype, value in values:
                        terms.append('%s %s.%s=%r' % (MATCH_MOD_OP_STR[op], attr, valtype, value))
            mlines.append('\nAND '.join(terms))
        olines = []
        changetype = self.odata['changetype']
        if changetype is not None: olines.append('changetype: %s' % changetype)
        if changetype == 'modify':
            controls = self.odata['mod_controls']
            if controls is not None:
                for control in controls:
                    olines.append('control: %s' % ' '.join(filter(None, control)))
            ops = self.odata['mod_ops']
            if ops is not None:
                for modop, modattr, modvalues in ops:
                    olines.append('%s: %s' % (MOD_OP_STR[modop], modattr))
                    if modvalues is not None:
                        for modvalue in modvalues:
                            olines.append('%s: %s' % (modattr, modvalue))
                    olines.append('-')
        elif changetype == 'add':
            ops = self.odata['mod_ops']
            if ops is not None:
                for modattr, modvalues in ops:
                    if modvalues is not None:
                        for modvalue in modvalues:
                            olines.append('%s: %s' % (modattr, modvalue))
        else:
            entry = self.odata['entry']
            if entry is not None:
                for attr, values in entry.items():
                    for value in values:
                        olines.append('%s: %s' % (attr, value))
        dn = self.odata['dn']
        if olines or dn:
            if dn is None: olines.insert(0, 'dn: <same DN>')
            else: olines.insert(0, 'dn: %s' % dn)
        return '%s%s%s%s' % (mlines and 'ON ' or '', '\nAND '.join(mlines),
                             olines and '\nAPPLY LDIF:\n' or '', '\n'.join(olines))
    def __repr__(self):
        return 'Rule<%r>' % self.__dict__
