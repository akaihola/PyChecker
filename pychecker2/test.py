import os
import sys
import unittest
import inspect
import glob

class Tester:
    def __init__(self):
        self.modules = []
        self.exit_status = 0
        self.verbosity = 1
        self.coverage = None

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
    files = glob.glob(os.path.join(root, 'utest', '*.py'))
    files.sort()
    for fname in files:
        fname = os.path.split(fname)[1] # remove path
        module = 'pychecker2.utest.' + os.path.splitext(fname)[0]
        if not module.endswith('_'):    # ignore __init__
            modules.append(module)
    return modules

def _root_path_to_file(fname):
    result = os.path.dirname(sys.argv[0])
    if not result:
        result = os.getcwd()
    if not result.startswith(os.sep):
        result = os.path.join(os.getcwd(), result)
    return os.path.normpath(result)

def main(args):
    import getopt
    try:
        opts, files = getopt.getopt(args, 'vc')
        for opt, arg in opts:
            if opt == '-v':
                test.verbosity += 1
            elif opt == '-c':
                test.coverage = 1
            else:
                raise Usage('unknown option ' + opt)
    except getopt.GetoptError, detail:
                raise Usage(str(detail))

    root = _root_path_to_file(sys.argv[0])
    pychecker2 = os.path.split(root)[0]
    sys.path.append(pychecker2)

    _make_coverage_dirs(root)
    test.modules = _modules(root)

    try:
        import trace
    except Exception, detail:
        if test.coverage:
            print 'Error: not tracing (%s)' % detail
        coverage = None

    if test.coverage:
        ignore = trace.Ignore(dirs = [sys.prefix, sys.exec_prefix])
        coverage = trace.Coverage(ignore)
        trace.run(coverage.trace, 'test()')
        trace.create_results_log(coverage.results(),
                                 os.path.join(root, 'coverage'))
    else:
        test()
        

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Usage, detail:
        err = sys.stderr
        print >>err, "Error: " + str(detail)
        print >>err
        print >>err, "Usage: %s [-v] [-c]" % sys.argv[0]
        sys.exit(1)
    else:
        sys.exit(test.exit_status)
