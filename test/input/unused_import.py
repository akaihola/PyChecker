# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

import sys

from os import path

import xml.sax as sax

from xml import dom

def do(dom=None): # older pycheckers treated dom as used
    print dom
