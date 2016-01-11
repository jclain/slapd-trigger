# -*- coding: utf-8 mode: python -*- vim:sw=4:sts=4:et:ai:si:sta:fenc=utf-8

__all__ = ()

from unittest import TestCase
from unittest import defaultTestLoader, TextTestRunner

from strules import *
from stenv import parse_sparam_value

class TestRule(TestCase):
    def test_replace_vars(self):
        r = Rule(None, None)
        data = dict(name='value')
        self.assertEquals(r'any\value', r.replace_vars(r'any\value', data))
        self.assertEquals(r'any\\value', r.replace_vars(r'any\\value', data))
        self.assertEquals(r'any\\\value', r.replace_vars(r'any\\\value', data))
        self.assertEquals(r'value', r.replace_vars(r'${name}', data))
        self.assertEquals(r'${name}', r.replace_vars(r'\${name}', data))
        self.assertEquals(r'\value', r.replace_vars(r'\\${name}', data))
        self.assertEquals(r'\\${name}', r.replace_vars(r'\\\${name}', data))
        self.assertEquals(r'\\value', r.replace_vars(r'\\\\${name}', data))

    def test_match_attr(self):
        r = Rule(None, None)
        self.assertTrue(r.match_attr(None, None))
        self.assertTrue(r.match_attr(None, 'any'))
        self.assertFalse(r.match_attr([], None))
        self.assertFalse(r.match_attr('any', None))
        self.assertFalse(r.match_attr(['any'], None))
        self.assertFalse(r.match_attr([], 'attr'))
        self.assertTrue(r.match_attr('attr', 'attr'))
        self.assertTrue(r.match_attr(['attr'], 'attr'))
        self.assertTrue(r.match_attr(['a', 'b', 'c'], 'b'))
        # case insensitive
        self.assertTrue(r.match_attr('attr', 'ATTR'))
        self.assertTrue(r.match_attr(['attr'], 'ATTR'))
        self.assertTrue(r.match_attr(['a', 'b', 'c'], 'B'))
        self.assertTrue(r.match_attr('ATTR', 'attr'))
        self.assertTrue(r.match_attr(['ATTR'], 'attr'))
        self.assertTrue(r.match_attr(['A', 'B', 'C'], 'b'))

    def test_match_value(self):
        r = Rule(None, None)
        self.assertTrue(r.match_value(None, None))
        self.assertTrue(r.match_value(None, 'any'))
        self.assertFalse(r.match_value([], None))
        self.assertFalse(r.match_value('any', None))
        self.assertFalse(r.match_value(['any'], None))
        self.assertFalse(r.match_value([], 'value'))
        self.assertTrue(r.match_value('value', 'value'))
        self.assertTrue(r.match_value(['value'], 'value'))
        self.assertTrue(r.match_value(['a', 'b', 'c'], 'b'))
        # case sensitive
        self.assertFalse(r.match_value('value', 'VALUE'))
        self.assertFalse(r.match_value(['value'], 'VALUE'))
        self.assertFalse(r.match_value(['a', 'b', 'c'], 'B'))
        self.assertFalse(r.match_value('VALUE', 'value'))
        self.assertFalse(r.match_value(['VALUE'], 'value'))
        self.assertFalse(r.match_value(['A', 'B', 'C'], 'b'))

    def test_match_dn(self):
        r = Rule(None, None)
        self.assertTrue(r.match_dn(None, None, 'any'))
        self.assertTrue(r.match_dn(None, 'any', 'any'))
        self.assertFalse(r.match_dn([], None, 'any'))
        self.assertFalse(r.match_dn('any', None, 'any'))
        self.assertFalse(r.match_dn(['any'], None, 'any'))
        ## one dn
        # exact
        self.assertTrue(r.match_dn('dc=univ-reunion,dc=fr', 'DC=UNIV-REUNION,DC=FR', 'exact'))
        self.assertTrue(r.match_dn('dc=univ-reunion,dc=fr', 'dc=univ-reunion,dc=fr', 'exact'))
        self.assertFalse(r.match_dn('dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr', 'exact'))
        self.assertFalse(r.match_dn('dc=univ-reunion,dc=fr', 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'exact'))
        # baseobject
        self.assertTrue(r.match_dn('dc=univ-reunion,dc=fr', 'dc=univ-reunion,dc=fr', 'baseobject'))
        self.assertFalse(r.match_dn('dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr', 'baseobject'))
        self.assertFalse(r.match_dn('dc=univ-reunion,dc=fr', 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'baseobject'))
        # regex
        self.assertFalse(r.match_dn('uid=\w+,dc=univ-reunion,dc=fr', 'dc=univ-reunion,dc=fr', 'regex'))
        self.assertTrue(r.match_dn('uid=\w+,dc=univ-reunion,dc=fr', 'uid=joe,dc=univ-reunion,dc=fr', 'regex'))
        self.assertFalse(r.match_dn('uid=\w+,dc=univ-reunion,dc=fr', 'uid=joe,ou=org,dc=univ-reunion,dc=fr', 'regex'))
        # onelevel
        self.assertFalse(r.match_dn('dc=univ-reunion,dc=fr', 'dc=univ-reunion,dc=fr', 'onelevel'))
        self.assertTrue(r.match_dn('dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr', 'onelevel'))
        self.assertFalse(r.match_dn('dc=univ-reunion,dc=fr', 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'onelevel'))
        # subtree
        self.assertTrue(r.match_dn('dc=univ-reunion,dc=fr', 'dc=univ-reunion,dc=fr', 'subtree'))
        self.assertTrue(r.match_dn('dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr', 'subtree'))
        self.assertTrue(r.match_dn('dc=univ-reunion,dc=fr', 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'subtree'))
        # children
        self.assertFalse(r.match_dn('dc=univ-reunion,dc=fr', 'dc=univ-reunion,dc=fr', 'children'))
        self.assertTrue(r.match_dn('dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr', 'children'))
        self.assertTrue(r.match_dn('dc=univ-reunion,dc=fr', 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'children'))
        ## singleton
        # exact
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr'], 'DC=UNIV-REUNION,DC=FR', 'exact'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr'], 'dc=univ-reunion,dc=fr', 'exact'))
        self.assertFalse(r.match_dn(['dc=univ-reunion,dc=fr'], 'ou=sub,dc=univ-reunion,dc=fr', 'exact'))
        self.assertFalse(r.match_dn(['dc=univ-reunion,dc=fr'], 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'exact'))
        # baseobject
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr'], 'dc=univ-reunion,dc=fr', 'baseobject'))
        self.assertFalse(r.match_dn(['dc=univ-reunion,dc=fr'], 'ou=sub,dc=univ-reunion,dc=fr', 'baseobject'))
        self.assertFalse(r.match_dn(['dc=univ-reunion,dc=fr'], 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'baseobject'))
        # regex
        self.assertFalse(r.match_dn(['uid=\w+,dc=univ-reunion,dc=fr'], 'dc=univ-reunion,dc=fr', 'regex'))
        self.assertTrue(r.match_dn(['uid=\w+,dc=univ-reunion,dc=fr'], 'uid=joe,dc=univ-reunion,dc=fr', 'regex'))
        self.assertFalse(r.match_dn(['uid=\w+,dc=univ-reunion,dc=fr'], 'uid=joe,ou=org,dc=univ-reunion,dc=fr', 'regex'))
        # onelevel
        self.assertFalse(r.match_dn(['dc=univ-reunion,dc=fr'], 'dc=univ-reunion,dc=fr', 'onelevel'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr'], 'ou=sub,dc=univ-reunion,dc=fr', 'onelevel'))
        self.assertFalse(r.match_dn(['dc=univ-reunion,dc=fr'], 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'onelevel'))
        # subtree
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr'], 'dc=univ-reunion,dc=fr', 'subtree'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr'], 'ou=sub,dc=univ-reunion,dc=fr', 'subtree'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr'], 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'subtree'))
        # children
        self.assertFalse(r.match_dn(['dc=univ-reunion,dc=fr'], 'dc=univ-reunion,dc=fr', 'children'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr'], 'ou=sub,dc=univ-reunion,dc=fr', 'children'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr'], 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'children'))
        ## list
        # exact
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'DC=UNIV-REUNION,DC=FR', 'exact'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'dc=univ-reunion,dc=fr', 'exact'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'ou=sub,dc=univ-reunion,dc=fr', 'exact'))
        self.assertFalse(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'exact'))
        # baseobject
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'dc=univ-reunion,dc=fr', 'baseobject'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'ou=sub,dc=univ-reunion,dc=fr', 'baseobject'))
        self.assertFalse(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'baseobject'))
        # regex
        self.assertFalse(r.match_dn(['uid=\w+,dc=univ-reunion,dc=fr', 'uid=\w+,ou=[oO]rg,dc=univ-reunion,dc=fr'], 'dc=univ-reunion,dc=fr', 'regex'))
        self.assertTrue(r.match_dn(['uid=\w+,dc=univ-reunion,dc=fr', 'uid=\w+,ou=[oO]rg,dc=univ-reunion,dc=fr'], 'uid=joe,dc=univ-reunion,dc=fr', 'regex'))
        self.assertTrue(r.match_dn(['uid=\w+,dc=univ-reunion,dc=fr', 'uid=\w+,ou=[oO]rg,dc=univ-reunion,dc=fr'], 'uid=joe,ou=org,dc=univ-reunion,dc=fr', 'regex'))
        # onelevel
        self.assertFalse(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'dc=univ-reunion,dc=fr', 'onelevel'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'ou=sub,dc=univ-reunion,dc=fr', 'onelevel'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'onelevel'))
        # subtree
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'dc=univ-reunion,dc=fr', 'subtree'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'ou=sub,dc=univ-reunion,dc=fr', 'subtree'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'subtree'))
        # children
        self.assertFalse(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'dc=univ-reunion,dc=fr', 'children'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'ou=sub,dc=univ-reunion,dc=fr', 'children'))
        self.assertTrue(r.match_dn(['dc=univ-reunion,dc=fr', 'ou=sub,dc=univ-reunion,dc=fr'], 'ou=sub,ou=sub,dc=univ-reunion,dc=fr', 'children'))

class TestEnv(TestCase):
    def test_parse_sparam_value(self):
        value, s = parse_sparam_value(r'')
        self.assertEquals(r'', value)
        self.assertEquals(r'', s)

        value, s = parse_sparam_value(r'   ')
        self.assertEquals(r'', value)
        self.assertEquals(r'', s)

        value, s = parse_sparam_value(r'abc!*$')
        self.assertEquals(r'abc!*$', value)
        self.assertEquals(r'', s)

        value, s = parse_sparam_value(r'abc!*$   ')
        self.assertEquals(r'abc!*$', value)
        self.assertEquals(r'', s)

        value, s = parse_sparam_value(r'""')
        self.assertEquals(r'', value)
        self.assertEquals(r'', s)

        value, s = parse_sparam_value(r'""  ')
        self.assertEquals(r'', value)
        self.assertEquals(r'', s)

        value, s = parse_sparam_value(r'"   "  ')
        self.assertEquals(r'   ', value)
        self.assertEquals(r'', s)

        value, s = parse_sparam_value(r'"abc!*$"')
        self.assertEquals(r'abc!*$', value)
        self.assertEquals(r'', s)

        value, s = parse_sparam_value(r'"with spaces !*$"')
        self.assertEquals(r'with spaces !*$', value)
        self.assertEquals(r'', s)

        value, s = parse_sparam_value(r'"with spaces !*$"')
        self.assertEquals(r'with spaces !*$', value)
        self.assertEquals(r'', s)

        value, s = parse_sparam_value(r'"with \" quotes"')
        self.assertEquals(r'with " quotes', value)
        self.assertEquals(r'', s)

        value, s = parse_sparam_value(r'"others \x \\ \\\\"')
        self.assertEquals(r'others \x \ \\', value)
        self.assertEquals(r'', s)

        value, s = parse_sparam_value(r'"others \\\" \\\\\" \\\\\x"')
        self.assertEquals(r'others \" \\" \\\x', value)
        self.assertEquals(r'', s)

def run_tests():
    import sys; this_module = sys.modules[__name__]
    tests = defaultTestLoader.loadTestsFromModule(this_module)
    TextTestRunner().run(tests)

if __name__ == '__main__':
    run_tests()
