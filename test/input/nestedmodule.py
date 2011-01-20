import struct

class MyClass(object):
    class NestedClass(object):
        myStruct = struct.Struct('!LLL')
