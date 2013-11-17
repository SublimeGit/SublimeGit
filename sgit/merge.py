# coding: utf-8
from functools import partial

import sublime
from sublime_plugin import WindowCommand

from .util import get_setting
from .cmd import GitCmd
from .helpers import GitBranchHelper, GitErrorHelper


class GitMergeCommand(WindowCommand, GitCmd, GitBranchHelper, GitErrorHelper):
    """
    Documentation coming soon.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        branches = self.get_branches(repo)
        choices = [name for c, name in branches if not c]

        self.window.show_quick_panel(choices, partial(self.on_done, repo, choices), sublime.MONOSPACE_FONT)

    def on_done(self, repo, choices, idx):
        if idx == -1:
            return

        cmd = ['merge', '--no-progress']

        extra_flags = get_setting('git_merge_flags')
        if isinstance(extra_flags, list):
            cmd.extend(extra_flags)

        branch = choices[idx]
        cmd.append(branch)

        exit, stdout, stderr = self.git(cmd, cwd=repo)
        if exit == 0:
            panel = self.window.get_output_panel('git-merge')
            panel.run_command('git_panel_write', {'content': stdout})
            self.window.run_command('show_panel', {'panel': 'output.git-merge'})
        else:
            sublime.error_message(self.format_error_message(stdout))
        self.window.run_command('git_status', {'refresh_only': True})
