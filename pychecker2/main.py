import os, sys
path = os.path.dirname(os.path.dirname(sys.argv[0]))
sys.path.append(path)

from pychecker2 import Check

# importing these incorportes these checks
from pychecker2 import ParseChecks
from pychecker2 import OpChecks
from pychecker2 import VariableChecks
from pychecker2 import ScopeChecks

class NullWriter:
    def write(self, s): pass
    def flush(self): pass

def main():
    import pychecker2.Options as Options
    options = Options.Options()

    for p in Check.passes:
        for checker in p:
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

    for p in Check.passes:
        for checker in p:
            print >>out, 'Running check', checker
            for f in files:
                checker.check(f, options)
                out.write('.')
                out.flush()
            print >>out

    result = 0
    files.sort()
    for f in files:
        if not f.warnings:
            continue
        result = 1
        f.warnings.sort()
        last_msg = None
        print
        for line, msg in f.warnings:
            if msg != last_msg:
                if line:
                    print '%s:%d %s' % (f.name, line, msg)
                else:
                    print '%s: %s' % (f.name, msg)
                last_msg = msg
        
    if not result:
        print >>out, None
    sys.exit(result)

if __name__ == "__main__":
    main()
