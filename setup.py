#!/usr/bin/env python

"""To use this setup script to install PyChecker:

	rename pychecker-version pychecker
	python pychecker/setup.py install

Contributed by:  Nicolas Chauvat
"""

from distutils.core import setup

if __name__ == '__main__' :
  setup(name		= "PyChecker",
        version		= "0.4beta",
        license		= "BSD-like",
        description	= "Python source code checking tool",
        author		= "Neal Norwitz, MetaSlash, Inc.",
        author_email	= "pychecker@metaslash.com",
        url		= "http://pychecker.sourceforge.net/",
        packages	= [ 'pychecker' ],
	#doc_files	= [ 'COPYRIGHT', 'VERSION', 'README', ],
        long_description = "PyChecker is a python source code checking tool to help you find common bugs. It is meant to find problems that are typically caught by a compiler. Because of the dynamic nature of python, some warnings may be incorrect; however, spurious warnings should be fairly infrequent."
        )

