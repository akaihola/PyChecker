
import sre 

class jj(sre.Scanner) :
    def __init__(self):
      sre.Scanner.__init__(self, None)

class jj2(sre.Scanner) :
    def __init__(self):
      "Warning don't call sre.Scanner.__init__()"
      print "don't call sre.Scanner.__init__()"

