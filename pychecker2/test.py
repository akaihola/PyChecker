import os
import sys
import unittest
import inspect
import pychecker2
import glob

class Tester:
    def __init__(self):
        self.modules = []
        self.exit_status = 0
        self.verbosity = 1

    def __call__(self):
        for m in self.modules:
            s = unittest.defaultTestLoader.loadTestsFromName(m)
            result = unittest.TextTestRunner(verbosity=self.verbosity).run(s)
            if not result.wasSuccessful():
                exit_status = 1
test = Tester()

class Usage(Exception): pass

def _make_coverage_dirs(root):
    coverage_dir = os.path.join(root, 'coverage', root[1:], 'utest')
    if not os.path.exists(coverage_dir):
        os.makedirs(coverage_dir)

def _modules(root):
    modules = []
    for fname in glob.glob(os.path.join(root, 'utest', '*.py')):
        fname = os.path.split(fname)[1] # remove path
        module = 'pychecker2.utest.' + os.path.splitext(fname)[0]
        if not module.endswith('_'):    # ignore __init__
            modules.append(module)
    return modules

def main(args):
    import getopt
    opts, files = getopt.getopt(args, 'v')
    for opt, arg in opts:
        if opt == '-v':
            test.verbosity += 1
        else:
            raise Usage('unknown option ' + opt)
    
    root = os.path.dirname(inspect.getsourcefile(pychecker2))
    _make_coverage_dirs(root)
    test.modules = _modules(root)

    try:
        import trace
    except Exception, detail:
        print 'Error: %s, not tracing' % `detail`
        test()
    else:
        ignore = trace.Ignore(dirs = [sys.prefix, sys.exec_prefix])
        coverage = trace.Coverage(ignore)
        trace.run(coverage.trace, 'test()')
        trace.create_results_log(coverage.results(), 'coverage')
        

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Usage, detail:
        err = sys.stderr
        print >>err, "Error: " + detail
        print >>err
        print >>err, "Usage: %s [-v]" % sys.argv[0]
        sys.exit(1)
    else:
        sys.exit(test.exit_status)
