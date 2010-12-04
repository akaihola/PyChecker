# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import dis

res = []

for name, number in dis.opmap.items():
    res.append((number, name))

res.sort()
for number, name in res:
    print "%4d %s" % (number, name)
