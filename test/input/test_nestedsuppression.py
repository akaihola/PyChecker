# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

class O(object):
    pass

def containerFirst():
    def first():
        __pychecker__ = 'no-objattrs'
        a = O()
        # this one should not trigger a warning since __pychecker__ hides it
        print a.nonexistent

    def second():
        b = O()
        # this one should trigger a warning
        print b.nonexistent

    first()
    second()

def containerSecond():
    def first():
        a = O()
        # this one should trigger a warning
        print a.nonexistent

    def second():
        __pychecker__ = 'no-objattrs'
        b = O()
        # this one should not trigger a warning since __pychecker__ hides it
        print b.nonexistent

    first()
    second()

def containerNeither():
    def first():
        a = O()
        # this one should trigger a warning
        print a.nonexistent

    def second():
        b = O()
        # this one should trigger a warning
        print b.nonexistent

    first()
    second()

def containerBoth():
    def first():
        __pychecker__ = 'no-objattrs'
        a = O()
        # this one should not trigger a warning since __pychecker__ hides it
        print a.nonexistent

    def second():
        __pychecker__ = 'no-objattrs'
        b = O()
        # this one should not trigger a warning since __pychecker__ hides it
        print b.nonexistent

    first()
    second()
