# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

'''
Tests related to string formatting.
'''

import unittest
import common

class StringFormatTestCase(common.TestCase):
    '''
    test that new string formatting options are allowed.
    '''
    def test_format(self):
        self.check('test_string_format')

if __name__ == '__main__':
    unittest.main()
