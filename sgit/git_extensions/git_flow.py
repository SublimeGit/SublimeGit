# coding: utf-8
from functools import partial
import sublime
from sublime_plugin import WindowCommand

from ..util import noop, StatusSpinner
from ..cmd import GitFlowCmd


enabled = True


__all__ = ['GitFlowInitCommand', 'GitFlowFeatureCommand', 'GitFlowFeatureStartCommand', 'GitFlowFeatureFinishCommand',
           'GitFlowReleaseCommand', 'GitFlowReleaseStartCommand', 'GitFlowReleaseFinishCommand', 'GitFlowHotfixStartCommand',
           'GitFlowHotfixFinishCommand']


class GitFlowWindowCmd(GitFlowCmd):

    def is_visible(self):
        return enabled

    def is_enabled(self):
        return enabled

    def get_branch_choices(self, repo, kind):
        lines = self.git_flow_lines([kind], cwd=repo)
        branches, choices = [], []
        lines = [l for l in lines if l.strip()]
        for l in sorted(lines, key=lambda x: (0 if x[0] == '*' else 1, x[2:])):
            current = l[0:2]
            name = l[2:]
            choices.append(['%s%s' % (current, name.strip())])
            branches.append(name)
        return branches, choices

    def show_branches_panel(self, repo, on_selection, *args, **kwargs):
        branches, choices = self.get_branch_choices(repo, *args, **kwargs)

        def on_done(idx):
            if idx != -1:
                branch = branches[idx]
                on_selection(branch)

        self.window.show_quick_panel(choices, on_done, sublime.MONOSPACE_FONT)

    def run_async_gitflow_with_panel(self, repo, cmd, progress, panel_name):
        self.panel = self.window.get_output_panel(panel_name)
        self.panel_name = panel_name
        self.panel_shown = False

        thread = self.git_flow_async(cmd, cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, progress)
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.%s' % self.panel_name})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})
        self.window.run_command('git_status', {'refresh_only': True})

    def run_sync_gitflow_with_panel(self, repo, cmd, panel_name):
        out = self.git_flow_string(cmd, cwd=repo)
        panel = self.window.get_output_panel(panel_name)
        panel.run_command('git_panel_write', {'content': out})
        self.window.run_command('show_panel', {'panel': 'output.%s' % panel_name})
        self.window.run_command('git_status', {'refresh_only': True})


class GitFlowInitCommand(GitFlowWindowCmd, WindowCommand):

    def run(self, defaults=True):
        repo = self.get_repo()
        if not repo:
            return
        self.run_async_gitflow_with_panel(repo, ['init', '-d'], "Initializing git-flow", "git-flow-init")


# Generic

class GitFlowStartCommand(GitFlowWindowCmd):

    def start(self, kind, base=False):
        repo = self.get_repo()
        if not repo:
            return

        self.kind = kind
        self.base = base
        self.window.show_input_panel('%s:' % self.kind.capitalize(), '', partial(self.on_select, repo), noop, noop)

    def on_select(self, repo, selection):
        selection = selection.strip()
        if not selection:
            return

        if self.base:
            self.window.show_input_panel('Base:', '', partial(self.on_complete, repo, selection), noop, noop)
        else:
            self.on_complete(repo, selection)

    def on_complete(self, repo, selection, base=None):
        cmd = [self.kind, 'start', selection]
        if base and base.strip():
            cmd.append(base.strip())

        self.run_sync_gitflow_with_panel(repo, cmd, 'git-flow-%s-start' % self.kind)
        self.window.run_command('git_status', {'refresh_only': True})


class GitFlowFinishCommand(GitFlowWindowCmd):

    def finish(self, kind):
        repo = self.get_repo()
        if not repo:
            return

        self.kind = kind
        self.show_branches_panel(repo, partial(self.on_complete, repo), self.kind)

    def on_complete(self, repo, selection):
        progress = "Finishing %s: %s" % (self.kind, selection)
        panel_name = 'git-flow-%s-finish' % self.kind
        self.run_async_gitflow_with_panel(repo, [self.kind, 'finish', selection], progress, panel_name)


# Start commands

class GitFlowFeatureStartCommand(GitFlowStartCommand, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self, base=False):
        self.start('feature', base)


class GitFlowReleaseStartCommand(GitFlowStartCommand, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self, base=False):
        self.start('release', base)


class GitFlowHotfixStartCommand(GitFlowStartCommand, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self, base=False):
        self.start('hotfix', base)


# Finish commands

class GitFlowFeatureFinishCommand(GitFlowFinishCommand, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        self.finish('feature')


class GitFlowReleaseFinishCommand(GitFlowFinishCommand, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        self.finish('release')


class GitFlowHotfixFinishCommand(GitFlowFinishCommand, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        self.finish('hotfix')


# Features

class GitFlowFeatureCommand(GitFlowWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return
        self.show_branches_panel(repo, noop, 'feature')


class GitFlowFeaturePublishCommand(GitFlowWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        pass


class GitFlowFeaturePullCommand(GitFlowWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        pass


# Releases

class GitFlowReleaseCommand(GitFlowWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return
        self.show_branches_panel(repo, noop, 'release')
