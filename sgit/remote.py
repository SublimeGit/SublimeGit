# coding: utf-8
from functools import partial

import sublime
from sublime_plugin import WindowCommand

from .util import append_view, StatusSpinner, get_setting, noop
from .cmd import GitCmd
from .helpers import GitRemoteHelper


NO_REMOTES = "No remotes have been configured. Please run Git: Add Remote to add a remote."
DELETE_REMOTE = "Are you sure you want to delete the remote %s?"

NO_ORIGIN_REMOTE = "You are not on any branch and no origin has been configured. Please run Git: Remote Add to add a remote."
NO_BRANCH_REMOTES = "No remotes have been configured for the branch %s and no origin exists. Please run Git: Remote Add to add a remote."

REMOTE_SHOW_TITLE_PREFIX = '*git-remote*: '


class GitFetchCommand(WindowCommand, GitCmd, GitRemoteHelper):

    def run(self):
        remote = self.get_current_remote_or_origin()

        if not remote:
            remotes = self.get_remotes()
            choices = self.format_quick_remotes(remotes)
            if not remotes:
                return sublime.error_message(NO_REMOTES)

            def on_done(idx):
                if idx != -1:
                    self.on_remote(choices[idx][0])

            self.window.show_quick_panel(choices, on_done)
        else:
            self.on_remote(remote)

    def on_remote(self, remote):
        self.panel = self.window.get_output_panel('git-fetch')
        self.panel_shown = False

        thread = self.git_async(['fetch', '-v', remote], on_data=self.on_data)
        runner = StatusSpinner(thread, "Fetching from %s" % remote)
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-fetch'})
        append_view(self.panel, d)
        self.panel.show(self.panel.size())


class GitPushCurrentBranchCommand(WindowCommand, GitCmd, GitRemoteHelper):

    def run(self):
        branch = self.get_current_branch()
        if not branch:
            return sublime.error_message("You really shouldn't push a detached head")

        branch_remote = self.get_remote_or_origin(branch)

        if not branch_remote:
            remotes = self.get_remotes()
            if not remotes:
                return sublime.error_message(NO_REMOTES)
            choices = self.format_quick_remotes(remotes)

            def on_done(idx):
                if idx == -1:
                    return
                branch_remote = choices[idx][0]
                self.on_remote(branch, branch_remote)

            self.window.show_quick_panel(choices, on_done)
        else:
            self.on_remote(branch, branch_remote)

    def on_remote(self, branch, branch_remote):
        self.git(['config', 'branch.%s.remote' % branch, branch_remote])

        merge_branch = self.get_merge_branch(branch)
        if not merge_branch:
            def on_done(rbranch):
                rbranch = rbranch.strip()
                if not rbranch:
                    return
                self.on_remote_branch(branch, branch_remote, 'refs/heads/' + rbranch)

            self.window.show_input_panel('Remote branch:', branch, on_done, noop, noop)
        else:
            self.on_remote_branch(branch, branch_remote, merge_branch)

    def on_remote_branch(self, branch, branch_remote, merge_branch):
        cmd = ['push', '-v', branch_remote, '%s:%s' % (branch, merge_branch)]
        if get_setting('git_set_upstream_on_push', False):
            cmd.append('--set-upstream')

        self.panel = self.window.get_output_panel('git-push')
        self.panel_shown = False

        thread = self.git_async(cmd, on_data=self.on_data)
        runner = StatusSpinner(thread, "Pushing %s to %s" % (branch, branch_remote))
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-push'})
        append_view(self.panel, d)
        self.panel.show(self.panel.size())


class GitPullCurrentBranchCommand(WindowCommand, GitCmd, GitRemoteHelper):

    def run(self):
        branch = self.get_current_branch()
        branch_remote = self.get_remote_or_origin(branch)

        if not branch_remote:
            remotes = self.get_remotes()
            if not remotes:
                return sublime.error_message(NO_REMOTES)
            choices = self.format_quick_remotes(remotes)

            def on_done(idx):
                if idx == -1:
                    return
                branch_remote = choices[idx][0]
                self.on_remote(branch, branch_remote)

            self.window.show_quick_panel(choices, on_done)
        else:
            self.on_remote(branch, branch_remote)

    def on_remote(self, branch, branch_remote):
        self.git(['config', 'branch.%s.remote' % branch, branch_remote])

        merge_branch = self.get_merge_branch(branch)
        if not merge_branch:
            remote_branches = self.get_remote_branches(branch_remote)
            if not remote_branches:
                return sublime.error_message("No branches on remote %s" % branch_remote)
            choices = self.format_quick_branches(remote_branches)

            def on_done(idx):
                if idx == -1:
                    return
                merge_branch = choices[idx][0]
                self.git(['config', 'branch.%s.merge' % branch, "refs/heads/%s" % merge_branch])
                self.on_remote_branch(branch, branch_remote, merge_branch)

            self.window.show_quick_panel(choices, on_done)
        else:
            self.on_remote_branch(branch, branch_remote, merge_branch)

    def on_remote_branch(self, branch, branch_remote, merge_branch):
        self.panel = self.window.get_output_panel('git-pull')
        self.panel_shown = False

        cmd = ['pull', '-v', branch_remote, '%s:%s' % (branch, merge_branch)]

        thread = self.git_async(cmd, on_data=self.on_data)
        runner = StatusSpinner(thread, "Pulling %s from %s" % (merge_branch, branch_remote))
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-pull'})
        append_view(self.panel, d)
        self.panel.show(self.panel.size())


class GitPushPullAllCommand(WindowCommand, GitCmd, GitRemoteHelper):

    def run(self, command):
        if command not in ('push', 'pull'):
            return

        branch = self.get_current_branch()
        branch_remote = self.get_remote_or_origin(branch)
        if not branch_remote:
            if not branch:
                return sublime.error_message(NO_ORIGIN_REMOTE)
            else:
                return sublime.error_message(NO_BRANCH_REMOTES % branch)

        if command == 'push':
            spinner_msg = "Pushing to %s" % branch_remote
        else:
            spinner_msg = "Pulling from %s" % branch_remote

        self.panel_name = 'git-%s' % command
        self.panel_shown = False
        self.panel = self.window.get_output_panel(self.panel_name)

        cmd = [command, '-v']
        if command == 'push' and get_setting('git_set_upstream_on_push', False):
            cmd.append('--set-upstream')

        thread = self.git_async(cmd, on_data=self.on_data)
        runner = StatusSpinner(thread, spinner_msg)
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.%s' % self.panel_name})
        append_view(self.panel, d)
        self.panel.show(self.panel.size())


class GitRemoteAddCommand(WindowCommand, GitCmd):

    def run(self):
        self.window.show_input_panel('Name:', '', self.on_name, noop, noop)

    def on_name(self, name):
        name = name.strip()
        # todo: check if name exists
        if not name:
            # todo: error message?
            return

        self.window.show_input_panel('Url:', '', partial(self.on_url, name), noop, noop)

    def on_url(self, name, url):
        url = url.strip()
        if not url:
            # todo: error message?
            return

        self.git(['remote', 'add', name, url])
        self.window.run_command('git_remote')


class GitRemoteCommand(WindowCommand, GitCmd, GitRemoteHelper):

    SHOW = 'Show'
    RM = 'Remove'
    RENAME = 'Rename'
    SET_URL = 'Set URL'
    PRUNE = 'Prune'

    REMOTE_ACTIONS = [
        [SHOW, 'git remote show <name>'],
        [RENAME, 'git remote rename <old> <new>'],
        [RM, 'git remote rm <name>'],
        [SET_URL, 'git remote set-url <name> <newurl>'],
        [PRUNE, 'git remote prune <name>'],
    ]

    ACTION_CALLBACKS = {
        SHOW: 'show_remote',
        RM: 'remove_remote',
        RENAME: 'rename_remote',
        SET_URL: 'remote_set_url',
        PRUNE: 'prune_remote'
    }

    def run(self):
        remotes = self.get_remotes()
        if not remotes:
            return sublime.error_message(NO_REMOTES)
        choices = self.format_quick_remotes(remotes)
        self.window.show_quick_panel(choices, partial(self.remote_panel_done, choices))

    def reset(self):
        self.window.run_command('git_remote')

    def remote_panel_done(self, choices, idx):
        if idx != -1:
            remote = choices[idx][0]
            self.window.show_quick_panel(self.REMOTE_ACTIONS, partial(self.action_panel_done, remote))

    def action_panel_done(self, remote, idx):
        if idx != -1:
            action = self.REMOTE_ACTIONS[idx][0]
            callback = self.ACTION_CALLBACKS[action]
            func = getattr(self, callback, None)
            if func:
                func(remote)

    def show_remote(self, remote):
        self.panel = self.window.get_output_panel('git-remote')
        self.panel_shown = False

        thread = self.git_async(['remote', 'show', remote], on_data=self.on_data)
        runner = StatusSpinner(thread, "Showing %s" % remote)
        runner.start()
        self.reset()

    def remove_remote(self, remote):
        if sublime.ok_cancel_dialog(DELETE_REMOTE % remote, "Delete"):
            self.git(['remote', 'rm', remote])
        self.reset()

    def rename_remote(self, remote):
        def on_done(new_name):
            new_name = new_name.strip()
            if new_name:
                self.git(['remote', 'rename', remote, new_name])
            self.reset()

        self.window.show_input_panel('Name:', remote, on_done, noop, self.reset)

    def remote_set_url(self, remote):
        url = self.get_remote_url(remote)
        self.window.show_input_panel('Url:', url, partial(self.on_url, remote), noop, self.reset)

    def on_url(self, remote, url):
        url = url.strip()
        if url:
            self.git(['remote', 'set-url', remote, url])
        self.reset()

    def prune_remote(self, remote):
        self.panel = self.window.get_output_panel('git-remote')
        self.panel_shown = False

        thread = self.git_async(['remote', 'prune', remote], on_data=self.on_data)
        runner = StatusSpinner(thread, "Pruning %s" % remote)
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-remote'})
        append_view(self.panel, d)
        self.panel.show(self.panel.size())
