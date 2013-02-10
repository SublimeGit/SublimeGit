# coding: utf-8
import time

import sublime
from sublime_plugin import WindowCommand

from .util import noop
from .cmd import GitCmd
from .helpers import GitStashHelper, GitErrorHelper


class GitStashWindowCmd(GitCmd, GitStashHelper, GitErrorHelper):

    def pop_or_apply_from_panel(self, action):
        stashes = self.get_stashes()

        if not stashes:
            sublime.error_message('No stashes. Use the Git: Stash command to stash changes')
            return

        callback = self.pop_or_apply_callback(action, stashes)
        panel = []
        for name, title in stashes:
            panel.append([title, "stash@{%s}" % name])

        self.window.show_quick_panel(panel, callback)

    def pop_or_apply_callback(self, action, stashes):
        def inner(choice):
            if choice != -1:
                name, _ = stashes[choice]
                exit_code, stdout = self.git(['stash', action, '-q', 'stash@{%s}' % name])
                if exit_code != 0:
                    sublime.error_message(self.format_error_message(stdout))
                window = sublime.active_window()
                if window:
                    window.run_command('git_status_refresh')

        return inner


class GitStashCommand(WindowCommand, GitStashWindowCmd):

    def run(self):
        def on_done(title):
            title = title.strip()
            self.git(['stash', 'save', '--', title])
            self.window.run_command('git_status_refresh')

        if self.git_exit_code(['diff', '--exit-code', '--quiet']) != 0:
            self.window.show_input_panel('Stash title:', '', on_done, noop, noop)
        else:
            sublime.error_message("No local changes to save")


class GitSnapshotCommand(WindowCommand, GitStashWindowCmd):

    def run(self):
        snapshot = time.strftime("Snapshot at %Y-%m-%d %H:%M:%S")
        self.git(['stash', 'save', '--', snapshot])
        self.git(['stash', 'apply', '-q', 'stash@{0}'])
        self.window.run_command('git_status_refresh')


class GitStashPopCommand(WindowCommand, GitStashWindowCmd):

    def run(self):
        self.pop_or_apply_from_panel('pop')


class GitStashApplyCommand(WindowCommand, GitStashWindowCmd):

    def run(self):
        self.pop_or_apply_from_panel('apply')
