# coding: utf-8
from functools import partial

import sublime
from sublime_plugin import WindowCommand, TextCommand

from .util import noop
from .cmd import GitCmd
from .helpers import GitStatusHelper, GitBranchHelper, GitErrorHelper, GitLogHelper
from .helpers import GitTagHelper


GIT_BRANCH_EXISTS_MSG = "The branch %s already exists. Do you want to overwrite it?"


class GitCheckoutWindowCmd(GitCmd, GitBranchHelper, GitLogHelper, GitErrorHelper):
    pass


class GitCheckoutBranchCommand(WindowCommand, GitCheckoutWindowCmd):
    """
    Check out an existing branch.

    This command allows you to select a branch from the quick bar
    to check out. The currently active branch (if any) is marked with an
    asterisk (*) to the left of its name.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        branches = self.get_branches(repo)
        choices = []
        for current, name in branches:
            choices.append('%s %s' % ('*' if current else ' ', name))

        self.window.show_quick_panel(choices, partial(self.on_done, repo, branches), sublime.MONOSPACE_FONT)

    def on_done(self, repo, branches, idx):
        if idx == -1:
            return

        current, branch = branches[idx]
        if current:
            return

        exit, stdout, stderr = self.git(['checkout', branch], cwd=repo)
        if exit == 0:
            panel = self.window.get_output_panel('git-checkout')
            panel.run_command('git_panel_write', {'content': stderr})
            self.window.run_command('show_panel', {'panel': 'output.git-checkout'})
        else:
            sublime.error_message(self.format_error_message(stderr))
        self.window.run_command('git_status', {'refresh_only': True})


class GitCheckoutTagCommand(WindowCommand, GitCheckoutWindowCmd, GitTagHelper):
    """
    Check out a specific tag.

    This command allows you to check out a specific tag. A list of
    available tags will be presented in the quick bar.

    After checkout, you will be in a detached head state.
    """

    def run(self, repo=None, tag=None):
        repo = repo or self.get_repo()
        if not repo:
            return

        if tag:
            self.on_tag(repo, tag)
        else:
            tags = self.get_tags(repo)
            if not tags:
                sublime.error_message("This repo does not contain any tags. Run Git: Add Tag to add one.")
                return

            choices = self.format_quick_tags(tags)

            def on_done(idx):
                if idx != -1:
                    tag = choices[idx][0]
                    self.on_tag(repo, tag)

            self.window.show_quick_panel(choices, on_done)

    def on_tag(self, repo, tag):
        exit, stdout, stderr = self.git(['checkout', 'tags/%s' % tag], cwd=repo)
        if exit == 0:
            panel = self.window.get_output_panel('git-checkout')
            panel.run_command('git_panel_write', {'content': stderr})
            self.window.run_command('show_panel', {'panel': 'output.git-checkout'})
        else:
            sublime.error_message(self.format_error_message(stderr))
        self.window.run_command('git_status', {'refresh_only': True})


class GitCheckoutCommitCommand(WindowCommand, GitCheckoutWindowCmd):
    """
    Check out a specific commit.

    This command allows you to check out a specific commit. The list
    of commits will be presented in the quick bar, containing the first
    line of the commit message, the abbreviated sha1, as well as a relative
    and absolute date in the local timezone.

    After checkout, you will be in a detached head state.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        log = self.get_quick_log(repo)
        hashes, choices = self.format_quick_log(log)
        self.window.show_quick_panel(choices, partial(self.on_done, repo, hashes))

    def on_done(self, repo, hashes, idx):
        if idx == -1:
            return

        commit = hashes[idx]
        exit, stdout, stderr = self.git(['checkout', commit], cwd=repo)
        if exit == 0:
            panel = self.window.get_output_panel('git-checkout')
            panel.run_command('git_panel_write', {'content': stderr})
            self.window.run_command('show_panel', {'panel': 'output.git-checkout'})
        else:
            sublime.error_message(self.format_error_message(stderr))
        self.window.run_command('git_status', {'refresh_only': True})


class GitCheckoutNewBranchCommand(WindowCommand, GitCheckoutWindowCmd):
    """
    Create a new branch from the current HEAD and switch to it.

    This command will show an input panel allowing you to name your new
    branch. After giving the branch a name, pressing enter will create
    the new branch and check it out. Pressing esc will cancel.

    If a branch with the given name already exists, you will be asked if
    you want to overwrite the branch. Selecting cancel will exit silently,
    without making any changes.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        self.window.show_input_panel("Branch:", "", partial(self.on_done, repo), noop, noop)

    def on_done(self, repo, branch):
        branch = branch.strip()
        if not branch:
            return

        b = '-b'

        branches = [n for _, n in self.get_branches(repo)]
        if branch in branches:
            if sublime.ok_cancel_dialog(GIT_BRANCH_EXISTS_MSG % branch, 'Overwrite'):
                b = '-B'
            else:
                return

        exit, stdout, stderr = self.git(['checkout', b, branch], cwd=repo)
        if exit == 0:
            panel = self.window.get_output_panel('git-checkout')
            panel.run_command('git_panel_write', {'content': stderr})
            self.window.run_command('show_panel', {'panel': 'output.git-checkout'})
        else:
            sublime.error_message(self.format_error_message(stderr))
        self.window.run_command('git_status', {'refresh_only': True})


class GitCheckoutCurrentFileCommand(TextCommand, GitCmd, GitStatusHelper):
    """
    Documentation coming soon.
    """

    def run(self, edit):
        filename = self.view.file_name()
        if not filename:
            sublime.error_message("Cannot checkout an unsaved file.")
            return

        repo = self.get_repo()
        if not repo:
            return

        if not self.file_in_git(repo, filename):
            sublime.error_message("The file %s is not tracked by git.")
            return

        exit, stdout, stderr = self.git(['checkout', '--quiet', '--', filename], cwd=repo)
        if exit == 0:
            sublime.status_message('Checked out %s' % filename)
            view = self.view
            sublime.set_timeout(partial(view.run_command, 'revert'), 50)
        else:
            sublime.error_message('git error: %s' % stderr)
