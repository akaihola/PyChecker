# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import unittest
import common

class MyTestCase(common.TestCase):
    def test_zope_interface(self):
        if not common.can_import('zope.interface'):
            self.skip = True # FIXME: interpret this

        self.check('test_zope_interface', '-q')
    
if __name__ == '__main__':
    unittest.main()
