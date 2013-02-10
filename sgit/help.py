# coding: utf-8
import os
import webbrowser

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


class GitVersionCommand(WindowCommand, GitCmd):

    def run(self):
        version = self.git_string(['--version'], cwd=os.path.realpath(''))
        sublime.error_message("You have %s" % version)
