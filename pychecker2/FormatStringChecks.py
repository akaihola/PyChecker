from pychecker2.Check import Check
from pychecker2.util import BaseVisitor
from pychecker2.Warning import Warning
from compiler import ast, walk
from types import *
import re

class Unknown(Exception): pass

def _compute_constant(node):
    try:
        if isinstance(node, ast.Const):
            return node.value
        if isinstance(node, ast.Add):
            return _compute_constant(node.left) + \
                   _compute_constant(node.right)
        if isinstance(node, ast.Mul):
            return _compute_constant(node.left) * \
                   _compute_constant(node.right)
    except TypeError:
        pass
    raise Unknown

format_re = re.compile('%([(]([a-zA-Z_]+)[)])?[ #+-]*'
                       '([0-9]*|[*])(|[.](|[*]|[0-9]*))([hlL])?'
                       '([diouxXeEfFgGcrs%])')

class FormatError(Exception):
    def __init__(self, position):
        self.position = position

FORMAT_UNKNOWN, FORMAT_DICTIONARY, FORMAT_TUPLE = range(3)

def _check_format(s):
    pos = 0
    specs = []
    while 1:
        pos = s.find('%', pos)
        if pos < 0:
            break
        match = format_re.search(s, pos)
        if not match or match.start(0) != pos:
            raise FormatError(pos)
        if match.group(7) != '%':
            specs.append( (match.group(2), match.group(3), match.group(5),
                           match.group(6), match.group(7)) )
        pos = match.end(0)
    return specs

def _compute_tuple_size(node):
    try:
        if isinstance(node, ast.Tuple):
            return len(node.nodes)
        if isinstance(node, ast.Add):
            return _compute_constant(node.left) + \
                   _compute_constant(node.right)
        if isinstance(node, ast.Mul):
            return _compute_constant(node.left) * \
                   _compute_constant(node.right)
    except TypeError:
        pass
    raise Unknown

class FormatStringCheck(Check):
    "Look for warnings in format strings"

    badFormat = \
              Warning('Report illegal format specifications in format strings',
                      'Bad format specifier at position %d (%s)')
    uselessModifier = \
              Warning('Report unused modifiers for format strings (l, h, L)',
                      'Modifier %s is not necessary')

    mixedFormat = \
              Warning('Report format strings which use both positional and named formats',
                      'Cannot mix positional and named formats (%s)')
    
    formatCount = \
              Warning('Report positional format string with the wrong '
                      'number of arguments',
                      'Wrong number of arguments supplied for format: '
                      '%d given %d required')
    unknownFormatName = \
              Warning('Report unknown names if locals() or globals() '
                      'are used for format strings',
                      'The name %s is not defined in %s')

    def check(self, file, unused_checker):
        if not file.parseTree:
            return

        for scope in file.scopes.values():
            class GetMod(BaseVisitor):
                def __init__(self):
                    self.mods = []
                def visitMod(self, node):
                    self.mods.append(node)
                    self.visitChildren(node)

            mods = walk(scope.node, GetMod()).mods
            for mod in mods:
                try:
                    s = _compute_constant(mod.left)
                except Unknown:
                    continue
                if not isinstance(s, StringType):
                    continue
                try:
                    formats = _check_format(s)
                except FormatError, detail:
                    part = 10
                    example = s[detail.position : detail.position + part]
                    example += len(s) > detail.position + part and "..." or ""
                    file.warning(mod, self.badFormat, detail.position, example)
                    continue
                if not formats:
                    continue

                count = len(formats)
                format_type = FORMAT_UNKNOWN
                names = []
                for f in formats:
                    name, width, precision, lmodifier, type = f
                    if lmodifier:
                        file.warning(mod, self.uselessModifier, lmodifier)
                    if name:
                        if format_type == FORMAT_TUPLE:
                            file.warning(mod, self.mixedFormat, '%s' % name)
                        format_type = FORMAT_DICTIONARY
                        names.append(name)
                    else:
                        if format_type == FORMAT_DICTIONARY:
                            file.warning(mod, self.mixedFormat, '%%%s' % type)
                        format_type = FORMAT_TUPLE
                    if width == '*':
                        count += 1
                    if precision == '*':
                        count += 1

                if format_type == FORMAT_TUPLE:
                    try:
                        n = _compute_tuple_size(mod.right) 
                        if n != count:
                            file.warning(mod, self.formatCount, n, count)
                    except Unknown:
                        pass
                else:
                    if isinstance(mod.right, ast.CallFunc) and \
                       isinstance(mod.right.node, ast.Name):
                        defines = []
                        if mod.right.node.name == 'locals':
                            defines = scope.defs.keys()
                        if mod.right.node.name == 'globals':
                            defines = scope.defs.keys()
                            for p in parents(scope):
                                defines.extend(p.defs.keys())
                        for n in names:
                            if not n in defines:
                                file.warning(mod, self.unknownFormatName,
                                             n, mod.right.node.name)

