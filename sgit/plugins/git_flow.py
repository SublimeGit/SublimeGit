# coding: utf-8
from functools import partial
import sublime
from sublime_plugin import WindowCommand

from ..util import noop, StatusSpinner
from ..cmd import Cmd


class GitFlowCmd(Cmd):
    __executable__ = 'git_flow'
    __bin__ = ['git-flow']


class GitFlowWindowCmd(GitFlowCmd):

    def get_branch_choices(self, kind):
        lines = self.git_flow_lines([kind])
        branches, choices = [], []
        lines = [l for l in lines if l.strip()]
        for l in sorted(lines, key=lambda x: (0 if x[0] == '*' else 1, x[2:])):
            current = l[0:2]
            name = l[2:]
            choices.append(['%s%s' % (current, name.strip())])
            branches.append(name)
        return branches, choices

    def show_branches_panel(self, on_selection, *args, **kwargs):
        branches, choices = self.get_branch_choices(*args, **kwargs)

        def on_done(idx):
            if idx != -1:
                branch = branches[idx]
                on_selection(branch)

        self.window.show_quick_panel(choices, on_done, sublime.MONOSPACE_FONT)

    def run_async_gitflow_with_panel(self, cmd, progress, panel_name):
        self.panel = self.window.get_output_panel(panel_name)
        self.panel_name = panel_name
        self.panel_shown = False

        thread = self.git_flow_async(cmd, on_data=self.on_data)
        runner = StatusSpinner(thread, progress)
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.%s' % self.panel_name})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})
        self.window.run_command('git_status', {'refresh_only': True})

    def run_sync_gitflow_with_panel(self, cmd, panel_name):
        out = self.git_flow_string(cmd)
        panel = self.window.get_output_panel(panel_name)
        panel.run_command('git_panel_write', {'content': out})
        self.window.run_command('show_panel', {'panel': 'output.%s' % panel_name})
        self.window.run_command('git_status', {'refresh_only': True})


class GitFlowInitCommand(WindowCommand, GitFlowWindowCmd):

    def run(self, defaults=True):
        self.run_async_gitflow_with_panel(['init', '-d'], "Initializing git-flow", "git-flow-init")


# Generic

class GitFlowStartCommand(GitFlowWindowCmd):

    def start(self, kind, base=False):
        self.kind = kind
        self.base = base
        self.window.show_input_panel('%s:' % self.kind.capitalize(), '', self.on_select, noop, noop)

    def on_select(self, selection):
        selection = selection.strip()
        if not selection:
            return

        if self.base:
            self.window.show_input_panel('Base:', '', partial(self.on_complete, selection), noop, noop)
        else:
            self.on_complete(selection)

    def on_complete(self, selection, base=None):
        cmd = [self.kind, 'start', selection]
        if base and base.strip():
            cmd.append(base.strip())

        self.run_sync_gitflow_with_panel(cmd, 'git-flow-%s-start' % self.kind)
        self.window.run_command('git_status', {'refresh_only': True})


class GitFlowFinishCommand(GitFlowWindowCmd):

    def finish(self, kind):
        self.kind = kind
        self.show_branches_panel(self.on_complete, self.kind)

    def on_complete(self, selection):
        progress = "Finishing %s: %s" % (self.kind, selection)
        panel_name = 'git-flow-%s-finish' % self.kind
        self.run_async_gitflow_with_panel([self.kind, 'finish', selection], progress, panel_name)


# Start commands

class GitFlowFeatureStartCommand(WindowCommand, GitFlowStartCommand):
    """
    Documentation coming soon.
    """

    def run(self, base=False):
        self.start('feature', base)


class GitFlowReleaseStartCommand(WindowCommand, GitFlowStartCommand):
    """
    Documentation coming soon.
    """

    def run(self, base=False):
        self.start('release', base)


class GitFlowHotfixStartCommand(WindowCommand, GitFlowStartCommand):
    """
    Documentation coming soon.
    """

    def run(self, base=False):
        self.start('hotfix', base)


# Finish commands

class GitFlowFeatureFinishCommand(WindowCommand, GitFlowFinishCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        self.finish('feature')


class GitFlowReleaseFinishCommand(WindowCommand, GitFlowFinishCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        self.finish('release')


class GitFlowHotfixFinishCommand(WindowCommand, GitFlowFinishCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        self.finish('hotfix')


# Features

class GitFlowFeatureCommand(WindowCommand, GitFlowWindowCmd):
    """
    Documentation coming soon.
    """

    def run(self):
        self.show_branches_panel(noop, 'feature')


class GitFlowFeaturePublishCommand(WindowCommand, GitFlowWindowCmd):
    """
    Documentation coming soon.
    """

    def run(self):
        pass


class GitFlowFeaturePullCommand(WindowCommand, GitFlowWindowCmd):
    """
    Documentation coming soon.
    """

    def run(self):
        pass


# Releases

class GitFlowReleaseCommand(WindowCommand, GitFlowWindowCmd):
    """
    Documentation coming soon.
    """

    def run(self):
        self.show_branches_panel(noop, 'release')
