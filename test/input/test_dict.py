# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# this should be fine, but failed with pychecker 0.8.18 on python 2.6
def func():
    d = { 'a': 1, 'b': 2}
    print d.keys()
