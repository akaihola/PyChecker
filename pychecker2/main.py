import os, sys
path = os.path.dirname(os.path.dirname(sys.argv[0]))
sys.path.append(path)

from pychecker2 import Options
from pychecker2 import ParseChecks
from pychecker2 import OpChecks
from pychecker2 import VariableChecks
from pychecker2 import ScopeChecks
from pychecker2 import ImportChecks

# importing these incorporates these checks

class NullWriter:
    def write(self, s): pass
    def flush(self): pass

def _print_warnings(f):
    if not f.warnings:
        return 0
    f.warnings.sort()
    last_msg = None
    for line, warning, args in f.warnings:
        if warning.value:
            msg = warning.message % args
            if msg != last_msg:
                print '%s:%s %s' % (f.name, line or '[unknown line]', msg)
                last_msg = msg
    if last_msg:
        print
    return 1
    

def main():
    options = Options.Options()
    checks = [ ParseChecks.ParseCheck(),
               OpChecks.OpCheck(),
               ImportChecks.ImportCheck(),
               VariableChecks.ShadowCheck(),
               VariableChecks.UnpackCheck(),
               VariableChecks.UnusedCheck(),
               VariableChecks.UnknownCheck(),
               VariableChecks.SelfCheck(),
               ScopeChecks.RedefineCheck() ]
    for checker in checks:
        checker.get_warnings(options)
        checker.get_options(options)

    try:
        files = options.process_options(sys.argv[1:])
    except Options.Error, detail:
        err = sys.stderr
        print >> err, "Error: %s" % detail
        options.usage(sys.argv[0], err)
        sys.exit(1)

    out = NullWriter()
    if options.verbose:
        out = sys.stdout

    modules = {}
    for f in files:
        print >>out, 'Checking file', checker
        for checker in checks:
            out.write('.')
            out.flush()
            checker.check(modules, f, options)
        print >>out
        if options.incremental:
            _print_warnings(f)

    result = 0
    if not options.incremental:
        files.sort()
        for f in files:
            result |=  _print_warnings(f)

        if not result:
            print >>out, None

    sys.exit(result)

if __name__ == "__main__":
    main()
