
import UserDict 

class jj(UserDict.UserDict) :
    def __init__(self):
      UserDict.UserDict.__init__(self, None)

class jj2(UserDict.UserDict) :
    def __init__(self):
      "Warning don't call UserDict.UserDict.__init__()"
      print "don't call UserDict.UserDict.__init__()"

