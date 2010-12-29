"""
Track loaded PyCheckerModules together with the directory they were loaded from.
This allows us to differentiate between loaded modules with the same name
but from different paths, in a way that sys.modules doesn't do.
"""

__pcmodules = {}

def getPCModule(moduleName, moduleDir=None):
    """
    @type  moduleName: str
    @param moduleDir:  if specified, the directory where the module can
                       be loaded from; allows discerning between modules
                       with the same name in a different directory.
                       Note that moduleDir can be the empty string, if
                       the module being tested lives in the current working
                       directory.
    @type  moduleDir:  str

    @rtype: L{pychecker.checker.PyCheckerModule}
    """

    global __pcmodules
    return __pcmodules.get((moduleName, moduleDir), None)

def getPCModules():
    """
    @rtype: list of L{pychecker.checker.PyCheckerModule}
    """
    global __pcmodules
    return __pcmodules.values()

def addPCModule(pcmodule):
    """
    @type  pcmodule: L{pychecker.checker.PyCheckerModule}
    """
    global __pcmodules
    __pcmodules[(pcmodule.moduleName, pcmodule.moduleDir)] = pcmodule
