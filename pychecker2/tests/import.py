from os.path import *
from sys import path as foo
import getopt                           # unused

def f(v):
    v.append(join(foo))                 # join from os.path
    v.append(__all__)                   # __all__ is unknown
