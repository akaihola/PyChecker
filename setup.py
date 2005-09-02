#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""
Python distutils setup script for pychecker.

This code was originally contributed by Nicolas Chauvat, and has been rewritten
to generalize it so it works properly with --prefix and other distutils
options.

This install script needs to customize two distutils behaviors: it needs to
install the documentation to the configured package install directory, and it
needs to create a pychecker (or pychecker.bat) script containing the correct
path to the installed checker.py module and the Python interpreter.

Nicolas' original attempt at this worked fine in the normal case (i.e. a root
user install).  However, because it assumed that the package directory was
always within sysconfig.get_python_lib(), it broke when users wanted to specify
a prefix or a home directory install to, etc.

After some research, I've decided that the best way to make this work is to
customize (override) some of the distutils action classes.  This way, we get
access to the distutils configuration and can "do the right thing" when options
are specified.  It turns out that I needed to customize the build_scripts and
install_data sections.  There are more notes below by each customized action.

@author: Kenneth J. Pronovici <pronovic@ieee.org>, after Nicolas Chauvat.
"""

###################
# Imported modules
###################

import sys
import os
from distutils import core
from distutils.util import execute
from distutils.command.install_data import install_data
from distutils.command.build_scripts import build_scripts


###############################
# Overridden distutils actions
###############################

class my_install_data(install_data):
   """
   Customized install_data distutils action.

   This customized action forces all data files to all be installed relative to
   the normal library install directory rather than in the standard location.
   This directory is usually something like /usr/share/python2.3/site-packages.   

   This action does not obey any --install-data flag that the user specifies.
   Distutils apparently does not provide a way to tell whether the install data
   directory on the Distribution class is "standard" or has already been
   overrwritten.  This means that we don't have a way to say "change this only
   if it hasn't been changed already".  All we can do is override the location
   all of the time.

   Note: If you want your files to go in the "pychecker" package directory,
   make sure that you specify "pychecker" as the prefix in the setup target.
   """
   def finalize_options(self):
      self.set_undefined_options('install', ('install_lib', 'install_dir'))
      install_data.finalize_options(self) # invoke "standard" action

class my_build_scripts(build_scripts):
   """
   Customized build_scripts distutils action.

   This action looks through the configured scripts list, and if "pychecker" is
   in the list, replaces that entry with the real name of the script to be
   created within the build directory (including the .bat extension if needed).
   Then, it builds the script (either Windows or shell style, depending on
   platform) using the proper path to the checker.py file and Python
   interpreter.  This is done through the execute() method, so that the action
   obeys the --dry-run flag, etc.

   This action completely ignores any scripts other than "pychecker" which are
   listed in the setup configuration, and it only does anything if "pychecker"
   is listed in the first place.  This way, new scripts with constant contents
   (if any) can be added to the setup configuration without writing any new
   code.
   """
   def run(self):
      if self.scripts is not None and "pychecker" in self.scripts:
         if sys.platform == "win32":
            script_path = os.path.join(self.build_dir, "pychecker.bat")
         else:
            script_path = os.path.join(self.build_dir, "pychecker")
         self.scripts.remove("pychecker")
         self.scripts.append(script_path)
         self.mkpath(self.build_dir)
         install_lib = self.distribution.get_command_obj("install").install_lib
         package_path = os.path.join(install_lib, "pychecker")
         self.execute(func=create_pychecker, args=[script_path, package_path], msg="Building %s" % script_path)
      build_scripts.run(self) # invoke "standard" action

def create_pychecker(script_path, package_path):
   """
   Creates the pychecker script at the indicated path.

   The pychecker script will be created to point to checker.py in the package
   directory, using the Python executable specified in sys.executable.  If the
   platform is Windows, a batch-style script will be created.  Otherwise, a
   Bourne-shell script will be created.  Note that we don't worry about what
   permissions mode the created file will have because the distutils install
   process takes care of that for us.

   @param script_path: Path to the script to be created
   @param package_path: Path to the package that checker.py can be found within

   @raise Exception: If script cannot be created on disk.
   """
   try:
      checker_path = os.path.join(package_path, "checker.py")
      if sys.platform == "win32":
         script_str = "%s %s %%1 %%2 %%3 %%4 %%5 %%6 %%7 %%8 %%9\n" % (sys.executable, checker_path)
      else:
         script_str = '#! /bin/sh\n\n%s %s "$@"\n' % (sys.executable, checker_path)
      open(script_path, "w").write(script_str)
   except Exception, e:
      print "ERROR: Unable to create %s: %s" % (script_path, e)
      raise e


######################
# Setup configuration
######################

CUSTOMIZED_ACTIONS = { 'build_scripts'  : my_build_scripts, 
                       'install_data'   : my_install_data,
                     }

DATA_FILES = [ 'COPYRIGHT', 'README', 'VERSION', 'CHANGELOG', 
                'KNOWN_BUGS', 'MAINTAINERS', 'TODO', 
             ]

LONG_DESCRIPTION = """
PyChecker is a tool for finding bugs in python source code.  It finds problems
that are typically caught by a compiler for less dynamic languages, like C and
C++. Because of the dynamic nature of Python, some warnings may be incorrect;
however, spurious warnings should be fairly infrequent.
"""

kw =  { 'name'             : "PyChecker",
        'version'          : "0.8.15",
        'license'          : "BSD-like",
        'description'      : "Python source code checking tool",
        'author'           : "Neal Norwitz, MetaSlash, Inc.",
        'author_email'     : "nnorwitz@gmail.com",
        'url'              : "http://pychecker.sourceforge.net/",
        'packages'         : [ 'pychecker', ],
        'scripts'          : [ "pychecker" ],   # note: will be replaced by customized action
        'data_files'       : [ ( "pychecker", DATA_FILES, ) ], 
        'long_description' : LONG_DESCRIPTION,
        'cmdclass'         : CUSTOMIZED_ACTIONS, 
      }

if hasattr(core, 'setup_keywords') and 'classifiers' in core.setup_keywords:
   kw['classifiers'] =  [ 'Development Status :: 4 - Beta',
                          'Environment :: Console',
                          'Intended Audience :: Developers',
                          'License :: OSI Approved :: BSD License',
                          'Operating System :: OS Independent',
                          'Programming Language :: Python',
                          'Topic :: Software Development :: Debuggers',
                          'Topic :: Software Development :: Quality Assurance',
                          'Topic :: Software Development :: Testing',
                        ]

if __name__ == '__main__' :
   core.setup(**kw)

