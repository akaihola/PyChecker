from pychecker2.Warning import Warning
from pychecker2 import Options

class WarningOpt(Options.BoolOpt):
    
    def __init__(self, longName, warning):
        self.warning = warning
        self.longName = longName

    def set_value(self, unused):
        self.warning.value = not self.warning.value
        
    def get_value(self):
        return self.warning.value

    def get_description(self):
        return self.warning.description

class Check:

    def __str__(self):
        return self.__class__.__name__

    def get_warnings(self, options):
        for attr in vars(self.__class__):
            object = getattr(self, attr)
            if isinstance(object, Warning):
                options.add(WarningOpt(attr, object))
    
    def get_options(self, options):
        pass
    
    def check(self, file, options):
        raise NotImplemented

pass1 = []
pass2 = []
passes = [pass1, pass2]
