
"Shouldn't be any warnings/errors"

import string

def describeSyntax(syntax):
    return string.join(['<%s>' % x.Description for x in syntax])

from sre import Scanner

class jj(Scanner) :
    def __init__(self):
      Scanner.__init__(self, None)

