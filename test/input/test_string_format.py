# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# This should be fine in 2.6 and above
def format_something(arg1):
    astring = "{0}-{1}-{2} ...its {this}!"
    return astring.format('3', '2', '1', this=arg1)
