#!/usr/local/bin/python

"""To use this setup script to install PyChecker:

        cd pychecker-version 
        python setup.py install

Contributed by:  Nicolas Chauvat
"""

import sys
import os
import tempfile

from distutils.core import setup
from distutils import sysconfig

def remove_file(file):
    try :
        os.unlink(file)
    except :
        pass

if __name__ == '__main__' :
    DOC_FILES = ('COPYRIGHT', 'README', 'VERSION', 'CHANGELOG', 'KNOWN_BUGS', 
                 'MAINTAINERS', 'TODO',)
    LONG_DESCRIPTION = \
"""PyChecker is a tool for finding bugs in python source code.
It finds problems that are typically caught by a compiler for less
dynamic languages, like C and C++. Because of the dynamic nature of python,
some warnings may be incorrect; however, spurious warnings should be
fairly infrequent."""

    install_dir = sysconfig.get_python_lib() + os.sep + 'pychecker'
    checker_py = install_dir + os.sep + 'checker.py'
    py_exe = sys.executable

    script_suffix = ''
    script_str = '#! /bin/sh\n\n%s %s "$@"\n' % (py_exe, checker_py)
    if sys.platform == 'win32' :
        script_str = '%s %s %%*\n' % (py_exe, checker_py)
        script_suffix = '.bat'

    LOCAL_SCRIPT = 'pychecker' + script_suffix
    LOCAL_SCRIPT = os.path.join(tempfile.gettempdir(), LOCAL_SCRIPT)
    remove_file(LOCAL_SCRIPT)

    try :
        fp = open(LOCAL_SCRIPT, "w")
        fp.write(script_str)
        fp.close()
        if sys.platform != 'mac' :
            os.chmod(LOCAL_SCRIPT, 0755)
    except :
        print "Unable to create utility script."
        raise

    setup(name                  = "PyChecker",
          version               = "0.8.10",
          license               = "BSD-like",
          description           = "Python source code checking tool",
          author                = "Neal Norwitz, MetaSlash, Inc.",
          author_email          = "pychecker@metaslash.com",
          url                   = "http://pychecker.sourceforge.net/",
          packages              = [ 'pychecker' ],
          data_files            = [ (install_dir, DOC_FILES) ],
          scripts               = [ LOCAL_SCRIPT, ],
          long_description      = LONG_DESCRIPTION
         )

    # cleanup old script file, it should have been installed
    remove_file(LOCAL_SCRIPT)

