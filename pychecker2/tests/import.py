from os.path import *
from sys import path as foo, argv as bar# bar not used
import getopt                           # getopt not used
import os.path as nifty                 # nifty not used

def f(v):
    v.append(join(foo))                 # join from os.path
    v.append(__all__)                   # __all__ is unknown

x = 7
if x == 100:
    from xYzZy import *                 # not found
    x = z

not_used = 13

