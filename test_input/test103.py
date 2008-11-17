"""Multiple generator expresstions should not cause a redefinition warning."""

def foo():
  print ' '.join(str(x) for x in range(10))
  print ' '.join(str(x) for x in range(10))
