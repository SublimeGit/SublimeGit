# coding: utf-8
import re
import os
import json
from sphinx import addnodes
from sphinx.domains import Domain, ObjType
from sphinx.directives import ObjectDescription
from sphinx.roles import XRefRole
from sphinx.util.docfields import GroupedField

from docutils import nodes
from docutils.statemachine import ViewList
from sphinx.util.compat import Directive
from sphinx.util.nodes import nested_parse_with_titles
from sphinx.util.docstrings import prepare_docstring


def import_class(name):
    module_name, cls = name.rsplit('.', 1)
    mod = __import__(module_name)
    mod = reduce(getattr, module_name.split('.')[1:], mod)
    return getattr(mod, cls)


class SublimeObject(ObjectDescription):
    pass


class SublimeWindowCommand(SublimeObject):

    doc_field_types = [
        GroupedField('shortcut', label='Keyboard Shortcut', names=('shortcut',)),
        GroupedField('setting', label='Settings', names=('setting',)),
    ]

    def handle_signature(self, sig, signode):
        signode += addnodes.desc_name(sig, sig)
        signode['command'] = sig
        return sig

    def needs_arglist(self):
        return False

    def add_target_and_index(self, name, sig, signode):
        slug = re.sub(r'\W+', '-', name).lower()

        if slug not in self.state.document.ids:
            signode['names'].append(slug)
            signode['ids'].append(slug)
            signode['first'] = (not self.names)
            self.state.document.note_explicit_target(signode)
            inv = self.env.domaindata['sublime']['objects']
            # if name in inv:
            #     self.state_machine.reporter.warning(
            #         'duplicate C object description of %s, ' % name +
            #         'other instance in ' + self.env.doc2path(inv[name][0]),
            #         line=self.lineno)
            inv[name] = (self.env.docname, self.objtype)
            #print inv[name]

        indextext = self.get_index_text(name)
        if indextext:
            self.indexnode['entries'].append(('single', indextext, slug, ''))

        # signode['ids'].append(clean_name)
        # self.env.domaindata['sublime'][sig] = (self.env.docname, '')
        # self.indexnode['entries'].append(('single', u'name', u'fullname', ''))

    def get_index_text(self, name):
        name = name.replace('Git: ', '')
        return u"%s (command)" % name


class SublimeTextCommand(SublimeObject):
    pass


class SublimeXRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        return "WUT!"


class SublimeDomain(Domain):
    """ Sublime Text domain """
    name = "sublime"
    label = "Sublime Text"

    object_types = {
        'windowcommand': ObjType('windowcommand', 'windowcmd')
    }
    directives = {
        'windowcommand': SublimeWindowCommand,
    }
    roles = {
        'windowcmd': SublimeXRefRole()
    }
    initial_data = {
        'objects': {}
    }


class AutoWindowCommand(Directive):
    has_content = True
    required_arguments = 1

    def cls_to_sublime_command(self, clsname):
        clsname = clsname[:-7]  # remove Command suffix
        clsname = re.sub(r'([a-z])([A-Z])', '\\1_\\2', clsname)  # Add underscore before all not-starting uppercase
        return clsname.lower()  # make it lowercase

    def get_sublime_caption(self, clsname):
        path = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../Default.sublime-commands'))

        command = self.cls_to_sublime_command(clsname)
        with open(path, 'r') as f:
            data = json.load(f)
            for cmd in data:
                if cmd['command'] == command:
                    return cmd['caption']

    def make_rst(self):
        classname = self.arguments[0]
        cls = import_class(classname)

        sublime_caption = self.get_sublime_caption(cls.__name__)

        doc = cls.__doc__
        yield ''
        yield '.. sublime:windowcommand:: {}'.format(sublime_caption)
        yield ''
        if doc:
            for line in prepare_docstring(doc):
                yield '    ' + line
            yield ''

    def run(self):
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.make_rst():
            result.append(line, '<autowindowcmd>')
        nested_parse_with_titles(self.state, result, node)
        return node.children


class AutoTextCommand(Directive):
    pass
