#!/usr/bin/env python

"""To use this setup script to install PyChecker:

	rename pychecker-version pychecker
	python pychecker/setup.py install

Contributed by:  Nicolas Chauvat
"""

from distutils.core import setup

if __name__ == '__main__' :
    DOC_FILES = [ 'COPYRIGHT', 'README', 'VERSION', ]
    LONG_DESCRIPTION = \
"""PyChecker is a tool for finding common bugs in python source code.
It finds problems that are typically caught by a compiler for less
dynamic languages, like C and C++. Because of the dynamic nature of python,
some warnings may be incorrect; however, spurious warnings should be
fairly infrequent."""

    setup(name			= "PyChecker",
	  version		= "0.5.1beta",
	  license		= "BSD-like",
	  description		= "Python source code checking tool",
	  author		= "Neal Norwitz, MetaSlash, Inc.",
	  author_email		= "pychecker@metaslash.com",
	  url			= "http://pychecker.sourceforge.net/",
	  packages		= [ 'pychecker' ],
	  #doc_files		= DOC_FILES,
	  long_description	= LONG_DESCRIPTION
	 )

