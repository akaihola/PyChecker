'd'

def x1(a, b, c = [], d = {}):
  c.reverse()
  d.update({ a: b})

def x2(a, b, c, d):
  c.reverse()
  d.update({ a: b})

def y(a, b, c = [], d = {}):
  print a, b, c, d

class X:
  'd'
  def x(self) : pass

def zz(x = X()):
    print x.x()

def zz2(a = [], b = {}):
    a[0] = b
    b[0] = a

