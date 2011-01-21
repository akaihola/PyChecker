# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4


class Foo(property):
     USE_PRIVATE = "usePrivate"
     def __init__(self, name,
                  fget=USE_PRIVATE,
                  fset=USE_PRIVATE,
                  fdel=USE_PRIVATE,
                  defaultVal=None,
                  descrip=None):
         privateName = '_'+name
         if fget == self.USE_PRIVATE:
             def f(obj):
                 if not obj.__dict__.has_key(privateName):
                     obj.__dict__[privateName] = copy.deepcopy(defaultVal)
                 return obj.__dict__[privateName]
             fget = f
         # other code omitted here (sets up 'fset' and 'fdel')
         super(SvtAttr, self).__init__(fget, fset, fdel, descrip)
