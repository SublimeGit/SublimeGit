# coding: utf-8
from functools import partial

import sublime
from sublime_plugin import WindowCommand

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
        choices = [name for current, name in branches if not current]

        self.window.show_quick_panel(choices, partial(self.on_done, repo, choices), sublime.MONOSPACE_FONT)

    def on_done(self, repo, choices, idx):
        if idx == -1:
            return

        branch = choices[idx]

        exit, stdout, stderr = self.git(['-c', 'color.diff=false', 'merge', '--no-progress', branch], cwd=repo)
        if exit == 0:
            panel = self.window.get_output_panel('git-merge')
            panel.run_command('git_panel_write', {'content': stdout})
            self.window.run_command('show_panel', {'panel': 'output.git-merge'})
        else:
            sublime.error_message(self.format_error_message(stdout))
        self.window.run_command('git_status', {'refresh_only': True})
