
class Warning:

    def __init__(self, description, message = None, value = 1):
        self.message = self.description = description
        if message:
            self.message = message
        self.value = value
        
    def __cmp__(self, other):
        return cmp(self.message, other.message)

    def __repr__(self):
        return repr(self.message)
