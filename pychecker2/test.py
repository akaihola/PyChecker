import os
import sys
import unittest
import inspect
import pychecker2
import glob

modules = []
exit_status = 0

def test():
    global exit_status
    for m in modules:
        s = unittest.defaultTestLoader.loadTestsFromName(m)
        result = unittest.TextTestRunner().run(s)
        if not result.wasSuccessful():
            exit_status = 1

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

def main():
    global modules
    root = os.path.dirname(inspect.getsourcefile(pychecker2))
    _make_coverage_dirs(root)
    modules = _modules(root)

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
    main()
    sys.exit(exit_status)
