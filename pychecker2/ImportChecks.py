
from pychecker2.Check import Check
from pychecker2.Check import Warning
from pychecker2.util import ScopeVisitor

from compiler import walk

class ImportCheck(Check):
    '''
Get 'from module import *' names hauled into the file and modules.
Figure out which names come from 'import name'.
    '''

    importError = Warning('Report/ignore imports that may fail',
                          'Error trying to import %s: %s')

    def check(self, unused_modules, file, unused_options):
        def try_import(name, node):
            try:
                return __import__(name, globals(), {}, [''])
            except ImportError, detail:
                file.warning(node, ImportCheck.importError, name, detail)
                return None
            
        class FromImportVisitor:

            def visitFrom(self, node, *scopes):
                m = try_import(node.modname, node)
                if m:
                    for module_name, local_name in node.names:
                        if module_name == '*':
                            for name in dir(m):
                                if not name.startswith('_'):
                                    scopes[-1].imports[name] = m
                        else:
                            scopes[-1].imports[local_name or module_name] = m

            def visitImport(self, node, *scopes):
                for module, name in node.names:
                    m = try_import(module, node)
                    if m:
                        # example: os.path stored under "os" or supplied name
                        base = module.split('.')[0]
                        scopes[-1].imports[name or base] = m


        if file.root_scope:
            walk(file.root_scope.node,
                 ScopeVisitor(file.scopes, FromImportVisitor()))
