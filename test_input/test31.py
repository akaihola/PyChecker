'doc'

class X:
  'doc'

class Y(X):
  'doc'

class Z(X):
  'doc'
  def __init__(self, arg):
    pass

def x():
  'should not cause a warning'
  print X()
  print Y()
  print Z('should create an exception since no __init__()')

def y():
  print X(a='should create an exception since no __init__()')
  print X('should create an exception since no __init__()')
  print Y(a='should create an exception since no __init__()')
  print Y('should create an exception since no __init__()')
  print Z(1, a='should create an exception since no __init__()')
  print Z(1, 2)

