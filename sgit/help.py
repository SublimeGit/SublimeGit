# coding: utf-8
import os
import webbrowser
try:
    from xml.etree import cElementTree as ET
except:
    from xml.etree import ElementTree as ET

import sublime
from sublime_plugin import WindowCommand

from .cmd import GitCmd


class GitHelpCommand(WindowCommand, GitCmd):

    def run(self):
        doc_path = self.git_string(['--html-path'], cwd=os.path.realpath(''))
        if not os.path.exists(doc_path):
            sublime.error_message('Directory %s does not exist. Have you deleted the git documentation?' % doc_path)
            return

        doc_files = {}
        for f in os.listdir(doc_path):
            if not f.endswith('.html'):
                continue
            key = f[4:-5] if f.startswith('git-') else f[:-5]
            url = 'file://%s' % os.path.join(doc_path, f)
            doc_files[key] = url

        choices = sorted(doc_files.keys())

        def on_done(idx):
            if idx != -1:
                choice = choices[idx]
                webbrowser.open(doc_files[choice])

        self.window.show_quick_panel(choices, on_done)


class GitHelpExtendedCommand(WindowCommand, GitCmd):

    def run(self):
        doc_path = self.git_string(['--html-path'], cwd=os.path.realpath(''))

        if not os.path.exists(doc_path):
            sublime.error_message('Directory %s does not exist. Have you deleted the git documentation?' % doc_path)
            return

        choices = []
        for f in os.listdir(doc_path):
            if not f.endswith('.html'):
                continue

            try:
                print os.path.join(doc_path, f)
                tree = ET.parse(os.path.join(doc_path, f))
                root = tree.getroot()
                h1 = root.find(".//{http://www.w3.org/1999/xhtml}h1").text.replace('Manual Page', '')
                firstp = root.find(".//{http://www.w3.org/1999/xhtml}p").text.split('\n', 1)[1].strip()
                choices.append([h1.replace('(1)', ''), firstp])
            except Exception, e:
                print e
                # handle user manual?
                pass

        print choices

        def on_done(idx):
            pass

        self.window.show_quick_panel(choices, on_done)


class GitVersionCommand(WindowCommand, GitCmd):

    def run(self):
        version = self.git_string(['--version'], cwd=os.path.realpath(''))
        sublime.error_message("You have %s" % version)
