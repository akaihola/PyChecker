'd'

def x():
    # these are broken, this is BAD code!!!
    i = ~~ 10
    while i > 0 :
      --i
    while i < 100 :
      ++i

    # these are fine
    j = 0
    while j > 0 :
      j = j - 1
    while j < 100 :
      j = j + 1
