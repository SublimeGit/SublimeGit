# coding: utf-8
from functools import partial

import sublime
from sublime_plugin import WindowCommand

from .util import create_panel
from .cmd import GitCmd
from .helpers import GitBranchHelper, GitErrorHelper


class GitMergeCommand(WindowCommand, GitCmd, GitBranchHelper, GitErrorHelper):

    def run(self):
        branches = self.get_branches()
        choices = [name for current, name in branches if not current]

        self.window.show_quick_panel(choices, partial(self.on_done, choices), sublime.MONOSPACE_FONT)

    def on_done(self, choices, idx):
        if idx == -1:
            return

        branch = choices[idx]

        exit_code, stdout = self.git(['merge', branch])
        if exit_code == 0:
            create_panel(self.window, 'git-merge', stdout)
        else:
            sublime.error_message(self.format_error_message(stdout))
        self.window.run_command('git_status_refresh')
