# -*- Mode: Python; test-case-name: test.test_pychecker_CodeChecks -*-
# vi:si:et:sw=4:sts=4:ts=4

# trigger opcode 99, DUP_TOPX

def duptopx():
    d = {}

    for i in range(0, 9):
        d[i] = i

    for k in d:
        # the += on a dict member triggers DUP_TOPX
        d[k] += 1
