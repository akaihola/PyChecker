'd'

def y():
    print '%d %f %s' % (1, 2.2, 'sdf')

    print '%d %f %s %d' % (1, 2.2, 'sdf')

    aaa = bbb = 1
    eee = 0
    print '%(aaa)d %(bbb)f %(ccc)s %(ddd)s' % locals()

    b = 0
    print '%()s %(b)d' % locals()

    print '%(b) %(aaa)d' % locals()
    print '%(aaa)d %(b)' % locals()

    print '%*d' % (2, 2)
    print '%*d' % (2, 2, 3)

    print '%*.*f' % (5, 2, 2.0)
    print '%*.*f' % (5, 2, 2.0, 3)

    fmt = '%d %s %d'
    # can't check this yet
    print fmt % (aaa, bbb)

