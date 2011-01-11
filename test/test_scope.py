# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

'''
Tests related to symbol scope.
'''

import unittest
import common

class NestedTestCase(common.TestCase):
    def test_nested(self):
        self.check('nested')
    
if __name__ == '__main__':
    unittest.main()
