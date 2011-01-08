# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

'''
Tests related to unused symbols.
'''

import unittest
import common

class UnusedImportTestCase(common.TestCase):
    todo = "Pychecker should catch the unused from ... import"
    '''
    '''
    def test_unused_import(self):
        self.check('unused_import')
    
if __name__ == '__main__':
    unittest.main()
