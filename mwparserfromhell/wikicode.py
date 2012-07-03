# -*- coding: utf-8  -*-
#
# Copyright (C) 2012 by Ben Kurtovic <ben.kurtovic@verizon.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import re

import mwparserfromhell
from mwparserfromhell.node import Node
from mwparserfromhell.string_mixin import StringMixIn
from mwparserfromhell.template import Template
from mwparserfromhell.text import Text

__all__ = ["Wikicode"]

FLAGS = re.I | re.S | re.U

class Wikicode(StringMixIn):
    def __init__(self, nodes):
        self._nodes = nodes

    def __unicode__(self):
        return "".join([unicode(node) for node in self.nodes])

    def _nodify(self, value):
        if isinstance(value, Wikicode):
            return value.nodes
        if isinstance(value, Node):
            return [value]
        if isinstance(value, str) or isinstance(value, unicode):
            return mwparserfromhell.parse(value).nodes
        error = "Needs string, Node, or Wikicode object, but got {0}: {1}"
        raise ValueError(error.format(type(value), value))

    def _get_children(self, node):
        yield node
        if isinstance(node, Template):
            for child in self._get_all_nodes(node.name):
                yield child
            for param in node.params:
                if param.showkey:
                    for child in self._get_all_nodes(param.name):
                        yield child
                for child in self._get_all_nodes(param.value):
                    yield child

    def _get_all_nodes(self, code):
        for node in code.nodes:
            for child in self._get_children(node):
                yield child

    def _do_recursive_index(self, obj):
        for i, node in enumerate(self.nodes):
            children = self._get_children(node)
            if isinstance(obj, Node):
                for child in children:
                    if child is obj:
                        return i
            else:
                if obj in children:
                    return i
        raise ValueError(obj)

    def _show_tree(self, code, lines, marker=None, indent=0):
        def write(*args):
            if lines and lines[-1] is marker:  # Continue from the last line
                lines.pop()  # Remove the marker
                last = lines.pop()
                lines.append(last + " ".join(args))
            else:
                lines.append("      " * indent + " ".join(args))

        for node in code.nodes:
            if isinstance(node, Template):
                write("{{", )
                self._show_tree(node.name, lines, marker, indent + 1)
                for param in node.params:
                    write("    | ")
                    lines.append(marker)  # Continue from this line
                    self._show_tree(param.name, lines, marker, indent + 1)
                    write("    = ")
                    lines.append(marker)  # Continue from this line
                    self._show_tree(param.value, lines, marker, indent + 1)
                write("}}")
            elif isinstance(node, Text):
                write(unicode(node))
            else:
                raise NotImplementedError(node)
        return lines

    @property
    def nodes(self):
        return self._nodes

    def get(self, index):
        return self.nodes[index]

    def set(self, index, value):
        nodes = self._nodify(value)
        if len(nodes) > 1:
            raise ValueError("Cannot coerce multiple nodes into one index")
        if index >= len(self.nodes) or -1 * index > len(self.nodes):
            raise IndexError("List assignment index out of range")
        self.nodex.pop(index)
        if nodes:
            self.nodes[index] = nodes[0]

    def index(self, obj, recursive=False):
        if recursive:
            return self._do_recursive_index()
        if isinstance(obj, Node):
            for i, node in enumerate(self.nodes):
                if node is obj:
                    return i
            raise ValueError(obj)
        return self.nodes.index(obj)

    def insert(self, index, value):
        nodes = self._nodify(value)
        for node in reversed(nodes):
            self.nodes.insert(index, node)

    def insert_before(self, obj, value, recursive=True):
        if obj not in self.nodes:
            raise KeyError(obj)
        self.insert(self.index(obj), value)

    def insert_after(self, obj, value, recursive=True):
        if obj not in self.nodes:
            raise KeyError(obj)
        self.insert(self.index(obj) + 1, value)

    def append(self, value):
        nodes = self._nodify(value)
        for node in nodes:
            self.nodes.append(node)

    def remove(self, node, recursive=True):
        self.nodes.pop(self.index(node))

    def ifilter(self, recursive=False, matches=None, flags=FLAGS,
                forcetype=None):
        if recursive:
            nodes = self._get_all_nodes(self)
        else:
            nodes = self.nodes
        for node in nodes:
            if not forcetype or isinstance(node, forcetype):
                if not matches or re.search(matches, unicode(node), flags):
                    yield node

    def ifilter_templates(self, recursive=False, matches=None, flags=FLAGS):
        return self.filter(recursive, matches, flags, forcetype=Template)

    def ifilter_text(self, recursive=False, matches=None, flags=FLAGS):
        return self.filter(recursive, matches, flags, forcetype=Text)

    def filter(self, recursive=False, matches=None, flags=FLAGS,
               forcetype=None):
        return list(self.ifilter(recursive, matches, flags, forcetype))

    def filter_templates(self, recursive=False, matches=None, flags=FLAGS):
        return list(self.ifilter_templates(recursive, matches, flags))

    def filter_text(self, recursive=False, matches=None, flags=FLAGS):
        return list(self.ifilter_text(recursive, matches, flags))

    def show_tree(self):
        marker = object()  # Random object we can find with certainty in a list
        print "\n".join(self._show_tree(self, [], marker))