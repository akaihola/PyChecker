class Check:

    def __str__(self):
        return self.__class__.__name__

    def get_options(self, options):
        pass
    
    def check(self, file, options):
        raise NotImplemented

pass1 = []
pass2 = []
passes = [pass1, pass2]
