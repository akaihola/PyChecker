
class File:
    def __init__(self, name):
        self.name = name
        self.parseTree = None
        self.scopes = {}
        self.root_scope = None
        self.warnings = []

    def __cmp__(self, other):
        return cmp(self.name, other.name)

    def warning(self, line, warn, *args):
	try:
	    line = line.lineno
        except AttributeError:
	    pass
        self.warnings.append( (line, warn, args) )


