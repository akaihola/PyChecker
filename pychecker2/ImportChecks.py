
from pychecker2.Check import Check
from pychecker2.Check import Warning
from pychecker2.util import BaseVisitor

from compiler import walk

class ImportCheck(Check):
    '''
Get 'from module import *' names hauled into the file and modules.
Figure out which names come from 'import name'.
    '''

    importError = Warning('Report/ignore imports that may fail',
                          'Error trying to import %s: %s')

    def check(self, unused_modules, file, unused_options):

        class FromImportVisitor(BaseVisitor):

            # return default for any name that isn't "visitFrom"
            def __getattr__(self, name):
                if name == 'visitFrom':
                    return self.visitFrom
                return self.default

            # Add a scope, if the node corresponds to a new scope
            def default(self, node, *scopes):
                try:
                    scopes = scopes + (file.scopes[node],)
                except KeyError:
                    pass
                for c in node.getChildNodes():
                    self.visit(c, *scopes)

            def visitFrom(self, node, *scopes):
                try:
                    m = __import__(node.modname, globals(), {}, [None])
                except ImportError, detail:
                    file.warning(node, ImportCheck.importError, node.modname, detail)
                else:
                    for module_name, local_name in node.names:
                        if module_name == '*':
                            for name in dir(m):
                                if not name.startswith('_'):
                                    scopes[-1].imports[name] = m
                        else:
                            scopes[-1].imports[local_name or module_name] = m

            def visitImport(self, node, *scopes):
                for module, name in node.names:
                    try:
                        m = __import__(module, globals(), {}, [None])
                    except ImportError, detail:
                        file.warning(node, ImportCheck.importError, node.modname, detail)
                    else:
                        # example: os.path stored under "os" or supplied name
                        base = module.split('.')[0]
                        scopes[-1].imports[name or base] = m


        if file.root_scope:
            walk(file.root_scope.node, FromImportVisitor())
