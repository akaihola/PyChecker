# -*- Mode: Python; test-case-name: test.test_pychecker_CodeChecks -*-
# vi:si:et:sw=4:sts=4:ts=4

# abridged version of twisted.trial.unittest.TestCase which triggered
# unimplemented opcode 40
class TestCase:
    _warnings = None

    def flushWarnings(self):
        self._warnings[:] = []
