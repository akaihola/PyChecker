'd'

def ttt(c):
  pass

def x():
  "should not complain about either, we can't check # args"
  columns = [ 1, 2 ]
  print zip(*columns)
  print ttt(*columns)

