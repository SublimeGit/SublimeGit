# coding: utf-8
import time

import sublime
from sublime_plugin import WindowCommand

from .util import noop
from .cmd import GitCmd
from .helpers import GitStashHelper, GitStatusHelper, GitErrorHelper


class GitStashWindowCmd(GitCmd, GitStashHelper, GitErrorHelper):

    def pop_or_apply_from_panel(self, action):
        repo = self.get_repo()
        if not repo:
            return

        stashes = self.get_stashes(repo)

        if not stashes:
            return sublime.error_message('No stashes. Use the Git: Stash command to stash changes')

        callback = self.pop_or_apply_callback(repo, action, stashes)
        panel = []
        for name, title in stashes:
            panel.append([title, "stash@{%s}" % name])

        self.window.show_quick_panel(panel, callback)

    def pop_or_apply_callback(self, repo, action, stashes):
        def inner(choice):
            if choice != -1:
                name, _ = stashes[choice]
                exit_code, stdout, stderr = self.git(['stash', action, '-q', 'stash@{%s}' % name], cwd=repo)
                if exit_code != 0:
                    sublime.error_message(self.format_error_message(stderr))
                window = sublime.active_window()
                if window:
                    window.run_command('git_status', {'refresh_only': True})
        return inner


class GitStashCommand(WindowCommand, GitCmd, GitStatusHelper):
    """
    Documentation coming soon.
    """

    def run(self, untracked=False):
        repo = self.get_repo()
        if not repo:
            return

        def on_done(title):
            title = title.strip()
            self.git(['stash', 'save', '--include-untracked' if untracked else None, '--', title], cwd=repo)
            self.window.run_command('git_status', {'refresh_only': True})

        # update the index
        self.git_exit_code(['update-index', '--refresh'], cwd=repo)

        # get files status
        untracked_files, unstaged_files, _ = self.get_files_status(repo)

        # check for if there's something to stash
        if not unstaged_files:
            if (untracked and not untracked_files) or (not untracked):
                return sublime.error_message("No local changes to save")

        self.window.show_input_panel('Stash title:', '', on_done, noop, noop)


class GitSnapshotCommand(WindowCommand, GitStashWindowCmd):
    """
    Documentation coming soon.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        snapshot = time.strftime("Snapshot at %Y-%m-%d %H:%M:%S")
        self.git(['stash', 'save', '--', snapshot], cwd=repo)
        self.git(['stash', 'apply', '-q', 'stash@{0}'], cwd=repo)
        self.window.run_command('git_status', {'refresh_only': True})


class GitStashPopCommand(WindowCommand, GitStashWindowCmd):
    """
    Documentation coming soon.
    """

    def run(self):
        self.pop_or_apply_from_panel('pop')


class GitStashApplyCommand(WindowCommand, GitStashWindowCmd):
    """
    Documentation coming soon.
    """

    def run(self):
        self.pop_or_apply_from_panel('apply')
