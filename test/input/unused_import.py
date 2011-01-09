# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import sys

from os import path

import xml.sax as sax

from unittest import case

def do(case=None): # older pycheckers treated case as used
    print case
