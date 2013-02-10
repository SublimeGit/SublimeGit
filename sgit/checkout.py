# coding: utf-8
from functools import partial

import sublime
from sublime_plugin import WindowCommand

from .util import noop, create_panel
from .cmd import GitCmd
from .helpers import GitBranchHelper, GitErrorHelper, GitLogHelper


GIT_BRANCH_EXISTS_MSG = "The branch %s already exists. Do you want to overwrite it?"


class GitCheckoutWindowCmd(GitCmd, GitBranchHelper, GitLogHelper, GitErrorHelper):

    pass


class GitCheckoutBranchCommand(WindowCommand, GitCheckoutWindowCmd):

    def run(self):
        branches = self.get_branches()
        choices = []
        for current, name in branches:
            choices.append('%s %s' % ('*' if current else ' ', name))

        self.window.show_quick_panel(choices, partial(self.on_done, branches), sublime.MONOSPACE_FONT)

    def on_done(self, branches, idx):
        if idx == -1:
            return

        current, branch = branches[idx]
        if current:
            return

        exit_code, stdout = self.git(['checkout', branch])
        if exit_code == 0:
            create_panel(self.window, 'git-checkout', stdout)
        else:
            sublime.error_message(self.format_error_message(stdout))
        self.window.run_command('git_status_refresh')


class GitCheckoutCommitCommand(WindowCommand, GitCheckoutWindowCmd):

    def run(self):
        hashes, choices = self.format_quick_log()
        self.window.show_quick_panel(choices, partial(self.on_done, hashes))

    def on_done(self, hashes, idx):
        if idx == -1:
            return

        commit = hashes[idx]
        exit_code, stdout = self.git(['checkout', commit])
        print "%s" % str([stdout])
        if exit_code == 0:
            sublime.message_dialog(stdout)
        else:
            sublime.error_message(self.format_error_message(stdout))


class GitCheckoutNewBranchCommand(WindowCommand, GitCheckoutWindowCmd):

    def run(self):
        self.window.show_input_panel("Branch:", "", self.on_done, noop, noop)

    def on_done(self, branch):
        branch = branch.strip()
        if not branch:
            return

        b = '-b'

        branches = [n for c, n in self.get_branches()]
        if branch in branches:
            if sublime.ok_cancel_dialog(GIT_BRANCH_EXISTS_MSG % branch, 'Overwrite'):
                b = '-B'
            else:
                return

        self.git(['checkout', b, branch])
        self.window.run_command('git_status_refresh')
