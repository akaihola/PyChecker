'doc'

import fnmatch

class X:
    'doc'
    def x(self):
        x = filter(lambda f, p = '' : fnmatch.fnmatch(f, p), [])
        print x

