# coding: utf-8
from functools import partial

import sublime
from sublime_plugin import WindowCommand

from .util import StatusSpinner, get_setting, noop
from .cmd import GitCmd
from .helpers import GitRemoteHelper


NO_REMOTES = u"No remotes have been configured. Remotes can be added with the Git: Add Remote command. Do you want to add a remote now?"
DELETE_REMOTE = u"Are you sure you want to delete the remote %s?"

NO_ORIGIN_REMOTE = u"You are not on any branch and no origin has been configured. Please run Git: Remote Add to add a remote."
NO_BRANCH_REMOTES = u"No remotes have been configured for the branch %s and no origin exists. Please run Git: Remote Add to add a remote."

REMOTE_SHOW_TITLE_PREFIX = '*git-remote*: '


class GitFetchCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Fetches git objects from the remote repository

    If the current branch is configured with a remote, this remote
    will be used for fetching. If there are no remotes specified for
    the current branch, the command will fall back to origin.

    In the situation where the current branch does not have a remote,
    and no origin is specified, a list of available remotes will be
    presented to choose from. If there are no remotes configured,
    you will be asked if you want to create a remote.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        remote = self.get_current_remote_or_origin(repo)

        if not remote:
            remotes = self.get_remotes(repo)
            choices = self.format_quick_remotes(remotes)
            if not remotes:
                if sublime.ok_cancel_dialog(NO_REMOTES, 'Add Remote'):
                    self.window.run_command('git_remote_add')
                    return

            def on_done(idx):
                if idx != -1:
                    self.on_remote(repo, choices[idx][0])

            self.window.show_quick_panel(choices, on_done)
        else:
            self.on_remote(repo, remote)

    def on_remote(self, repo, remote):
        self.panel = self.window.get_output_panel('git-fetch')
        self.panel_shown = False

        thread = self.git_async(['fetch', '-v', remote], cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Fetching from %s" % remote)
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-fetch'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})


class GitPushCurrentBranchCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Push the current branch to a remote

    This is the command to use if you are pushing a branch to a remote
    for the first time. Will push the current branch to a specified branch
    on the given remote, creating the remote branch if it doesn't already
    exist. Can also optionally set up the current branch to track the
    remote branch for future push, pull and fetch commands.

    If tracking has already been set up for the current branch, it
    will be used.

    If the current branch does not have a remote, origin will be used
    if it exists, otherwise you will be asked to select a remote. If
    there are no remotes, you will be asked to add one.

    If remote tracking has not been set up for the current branch,
    you will be asked to supply a name to use for the branch on the
    remote. By default, the current branch name will be suggested.

    :setting git_set_upstream_on_push: If set to ``true``, the flag
        ``--set-upstream`` will be used when pushing the branch.
        This will set up the branch to track the remote branch, so
        that argument-less pull, push and fetch will work. Set to
        ``false`` to disable. Default: ``true``

    .. warning::

        Trying to push when in a detached head state will give an error
        message. This is not generally something you want to do.

    .. note::

        This command shares a lot of similarities with the excellent
        git-publish command, which can be found at
        https://github.com/gavinbeatty/git-publish.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        branch = self.get_current_branch(repo)
        if not branch:
            return sublime.error_message("You really shouldn't push a detached head")

        branch_remote = self.get_remote_or_origin(repo, branch)

        if not branch_remote:
            remotes = self.get_remotes(repo)
            if not remotes:
                if sublime.ok_cancel_dialog(NO_REMOTES, 'Add Remote'):
                    self.window.run_command('git_remote_add')
                    return
            choices = self.format_quick_remotes(remotes)

            def on_done(idx):
                if idx == -1:
                    return
                branch_remote = choices[idx][0]
                self.on_remote(repo, branch, branch_remote)

            self.window.show_quick_panel(choices, on_done)
        else:
            self.on_remote(repo, branch, branch_remote)

    def on_remote(self, repo, branch, branch_remote):
        self.git(['config', 'branch.%s.remote' % branch, branch_remote], cwd=repo)

        merge_branch = self.get_merge_branch(repo, branch)
        if not merge_branch:
            def on_done(rbranch):
                rbranch = rbranch.strip()
                if not rbranch:
                    return
                self.on_remote_branch(repo, branch, branch_remote, 'refs/heads/' + rbranch)

            self.window.show_input_panel('Remote branch:', branch, on_done, noop, noop)
        else:
            self.on_remote_branch(repo, branch, branch_remote, merge_branch)

    def on_remote_branch(self, repo, branch, branch_remote, merge_branch):
        cmd = ['push', '-v', branch_remote, '%s:%s' % (branch, merge_branch)]
        if get_setting('git_set_upstream_on_push', False):
            cmd.append('--set-upstream')

        self.panel = self.window.get_output_panel('git-push')
        self.panel_shown = False

        thread = self.git_async(cmd, cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Pushing %s to %s" % (branch, branch_remote))
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-push'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})


class GitPullCurrentBranchCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Documentation coming soon.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        branch = self.get_current_branch(repo)
        branch_remote = self.get_remote_or_origin(repo, branch)

        if not branch_remote:
            remotes = self.get_remotes(repo)
            if not remotes:
                if sublime.ok_cancel_dialog(NO_REMOTES, 'Add Remote'):
                    self.window.run_command('git_remote_add')
                    return
            choices = self.format_quick_remotes(remotes)

            def on_done(idx):
                if idx == -1:
                    return
                branch_remote = choices[idx][0]
                self.on_remote(repo, branch, branch_remote)

            self.window.show_quick_panel(choices, on_done)
        else:
            self.on_remote(repo, branch, branch_remote)

    def on_remote(self, repo, branch, branch_remote):
        self.git(['config', 'branch.%s.remote' % branch, branch_remote], cwd=repo)

        merge_branch = self.get_merge_branch(repo, branch)
        if not merge_branch:
            remote_branches = self.get_remote_branches(repo, branch_remote)
            if not remote_branches:
                return sublime.error_message("No branches on remote %s" % branch_remote)
            choices = self.format_quick_branches(remote_branches)

            def on_done(idx):
                if idx == -1:
                    return
                merge_branch = choices[idx][0]
                self.git(['config', 'branch.%s.merge' % branch, "refs/heads/%s" % merge_branch], cwd=repo)
                self.on_remote_branch(repo, branch, branch_remote, merge_branch)

            self.window.show_quick_panel(choices, on_done)
        else:
            self.on_remote_branch(repo, branch, branch_remote, merge_branch)

    def on_remote_branch(self, repo, branch, branch_remote, merge_branch):
        self.panel = self.window.get_output_panel('git-pull')
        self.panel_shown = False

        cmd = ['pull', '-v', branch_remote, '%s:%s' % (branch, merge_branch)]

        thread = self.git_async(cmd, cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Pulling %s from %s" % (merge_branch, branch_remote))
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-pull'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})


class GitPushPullAllCommand(WindowCommand, GitCmd, GitRemoteHelper):

    def run(self, command):
        if command not in ('push', 'pull'):
            return

        repo = self.get_repo()
        if not repo:
            return

        branch = self.get_current_branch(repo)
        branch_remote = self.get_remote_or_origin(repo, branch)
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

        thread = self.git_async(cmd, cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, spinner_msg)
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.%s' % self.panel_name})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})


class GitPushCommand(WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        return self.window.run_command('git_push_pull_all', {'command': 'push'})


class GitPullCommand(WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        return self.window.run_command('git_push_pull_all', {'command': 'pull'})


class GitRemoteAddCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Add a named git remote at a given URL

    You will be asked to provide the name and url of the remote (see below).
    Press ``enter`` to select the value. If you want to cancel, press ``esc``.

    After completion, the Git: Remote command will be run, to allow for
    further management of remotes.

    **Name:**
        The name of the remote. By convention, the name *origin* is used
        for the "main" remote. Therefore, if your repository does not
        have any remotes, the initial suggestion for the name will be *origin*.
    **Url:**
        The git url of the remote repository, in any format that git understands.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        remotes = self.get_remotes()
        initial = 'origin' if not remotes else ''

        self.window.show_input_panel('Name:', initial, partial(self.on_name, repo), noop, noop)

    def on_name(self, repo, name):
        name = name.strip()
        # todo: check if name exists
        if not name:
            # todo: error message?
            return

        self.window.show_input_panel('Url:', '', partial(self.on_url, repo, name), noop, noop)

    def on_url(self, repo, name, url):
        url = url.strip()
        if not url:
            # todo: error message?
            return

        self.git(['remote', 'add', name, url], cwd=repo)
        self.window.run_command('git_remote')


class GitRemoteCommand(WindowCommand, GitCmd, GitRemoteHelper):
    """
    Manage git remotes

    Presents s list of remotes, including their push and pull urls.
    Select the remote to perform an action on it. After an action has
    been performed, the list will show up again to allow for further
    editing of remotes. To cancel, press ``esc``.

    Available actions:

    **Show**
        Show information about the remote. This includes the
        push and pull urls, the current HEAD, the branches tracked,
        and the local branches which are set up for push and pull.

        The result will be displayed in a panel in the bottom of
        the Sublime Text window.

    **Rename**
        Rename the selected remote. An input field will appear
        allowing you to write a new name for the remote. If a new
        name is not provided, or ``esc`` is pressed, the action
        will be aborted.

    **Remove**
        Remove the selected remote. All remote-tracking branches,
        and configuration for the remote is removed. You will be
        asked for confirmation before removing the remote.

    **Set URL**
        Change the URL for the selected remote. An input fiels
        will appear allowing you to specify a new URL. The given
        URL will be used for both the push and pull URL. If a new
        URL isn't specified, or ``esc`` is pressed, the URL will
        not be updated.

    **Prune**
        Delete all stale remote-tracking branches for the selected
        remote. Any remote-tracking branches in the local repository
        which are no longer in the remote repository will be removed.

    """

    SHOW = 'Show'
    RENAME = 'Rename'
    RM = 'Remove'
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

    def run(self, repo=None):
        repo = repo or self.get_repo()
        if not repo:
            return

        remotes = self.get_remotes(repo)
        if not remotes:
            if sublime.ok_cancel_dialog(NO_REMOTES, 'Add Remote'):
                self.window.run_command('git_remote_add')
                return

        choices = self.format_quick_remotes(remotes)
        self.window.show_quick_panel(choices, partial(self.remote_panel_done, repo, choices))

    def reset(self, repo):
        self.window.run_command('git_remote', {'repo': repo})

    def remote_panel_done(self, repo, choices, idx):
        if idx != -1:
            remote = choices[idx][0]

            def on_remote():
                self.window.show_quick_panel(self.REMOTE_ACTIONS, partial(self.action_panel_done, repo, remote))

            sublime.set_timeout(on_remote, 50)

    def action_panel_done(self, repo, remote, idx):
        if idx != -1:
            action = self.REMOTE_ACTIONS[idx][0]
            callback = self.ACTION_CALLBACKS[action]
            func = getattr(self, callback, None)
            if func:
                func(repo, remote)

    def show_remote(self, repo, remote):
        self.panel = self.window.get_output_panel('git-remote')
        self.panel_shown = False

        thread = self.git_async(['remote', 'show', remote], cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Showing %s" % remote)
        runner.start()
        self.reset(repo)

    def remove_remote(self, repo, remote):
        if sublime.ok_cancel_dialog(DELETE_REMOTE % remote, "Delete"):
            self.git(['remote', 'rm', remote], cwd=repo)
        self.reset(repo)

    def rename_remote(self, repo, remote):
        def on_done(new_name):
            new_name = new_name.strip()
            if new_name:
                self.git(['remote', 'rename', remote, new_name], cwd=repo)
            self.reset(repo)

        self.window.show_input_panel('Name:', remote, on_done, noop, self.reset)

    def remote_set_url(self, repo, remote):
        url = self.get_remote_url(repo, remote)
        self.window.show_input_panel('Url:', url, partial(self.on_url, repo, remote), noop, self.reset)

    def on_url(self, repo, remote, url):
        url = url.strip()
        if url:
            self.git(['remote', 'set-url', remote, url], cwd=repo)
        self.reset(repo)

    def prune_remote(self, repo, remote):
        self.panel = self.window.get_output_panel('git-remote')
        self.panel_shown = False

        thread = self.git_async(['remote', 'prune', remote], cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Pruning %s" % remote)
        runner.start()
        self.reset(repo)

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-remote'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})
