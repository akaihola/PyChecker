
"doc"

from metaslash.db import db

class X(db.Record) :
    "doc"
    def __init__(self):
	"shouldn't be a warning"
        db.Record.__init__(self, "")

class Y(Exception):
    "doc"
    def __init__(self, err):
	"this shouldn't produce a warning"
    	Exception.__init__(self, err)

def uuu(func):
    "shouldn't crash"
    return tuple([i for i in func() if func(globals()[i])])

def yyy():
    "shouldn't crash"
    map(apply, globals().keys(),
	        ((),) * len(globals()), globals().values())

