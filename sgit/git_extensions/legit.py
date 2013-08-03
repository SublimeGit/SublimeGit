# coding: utf-8
from functools import partial

import sublime
from sublime_plugin import WindowCommand

from ..util import noop, StatusSpinner
from ..cmd import LegitCmd


enabled = True


__all__ = ['LegitSwitchCommand', 'LegitSyncCommand', 'LegitPublishCommand', 'LegitUnpublishCommand',
           'LegitHarvestCommand', 'LegitSproutCommand', 'LegitGraftCommand', 'LegitBranchesCommand']


class LegitWindowCmd(LegitCmd):

    def is_visible(self):
        return enabled

    def is_enabled(self):
        return enabled

    def get_branch_choices(self, repo, filter=('published', 'unpublished')):
        lines = self.legit_lines(['branches'], cwd=repo)
        branches, choices = [], []
        for l in lines:
            if not l:
                continue
            current = l[0:2]
            name, pub = l[2:].split(None, 1)
            pub = pub.strip(' \t()')
            if not pub in filter:
                continue
            choices.append(['%s%s' % (current, name.strip()), '  %s' % pub])
            branches.append(name)
        return branches, choices

    def show_branches_panel(self, repo, on_selection, *args, **kwargs):
        branches, choices = self.get_branch_choices(repo, *args, **kwargs)

        def on_done(idx):
            if idx != -1:
                branch = branches[idx]
                on_selection(branch)

        self.window.show_quick_panel(choices, on_done, sublime.MONOSPACE_FONT)

    def run_async_legit_with_panel(self, repo, cmd, progress, panel_name):
        self.panel = self.window.get_output_panel(panel_name)
        self.panel_name = panel_name
        self.panel_shown = False

        thread = self.legit_async(cmd, cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, progress)
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.%s' % self.panel_name})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})


class LegitSwitchCommand(LegitWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return
        self.show_branches_panel(repo, partial(self.switch, repo))

    def switch(self, repo, branch):
        out = self.legit_string(['switch', branch], cwd=repo)
        panel = self.window.get_output_panel('legit-switch')
        panel.run_command('git_panel_write', {'content': out})
        self.window.run_command('show_panel', {'panel': 'output.legit-switch'})


class LegitSyncCommand(LegitWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self, select_branch=False):
        repo = self.get_repo()
        if not repo:
            return

        if select_branch:
            self.show_branches_panel(repo, partial(self.sync, repo), filter=('published',))
        else:
            self.sync(repo)

    def sync(self, repo, branch=None):
        if branch:
            progress = "Syncing %s" % branch
        else:
            progress = "Syncing"
        self.run_async_legit_with_panel(repo, ['sync', branch], progress, 'legit-sync')


class LegitPublishCommand(LegitWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        self.show_branches_panel(repo, partial(self.publish, repo), filter=('unpublished',))

    def publish(self, repo, branch):
        self.run_async_legit_with_panel(repo, ['publish', branch], "Publishing %s" % branch, 'legit-publish')


class LegitUnpublishCommand(LegitWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        self.show_branches_panel(repo, partial(self.unpublish, repo), filter=('published',))

    def unpublish(self, repo, branch):
        self.run_async_legit_with_panel(repo, ['unpublish', branch], "Unpublishing %s" % branch, 'legit-unpublish')


class LegitHarvestCommand(LegitWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self, select_branch=False):
        repo = self.get_repo()
        if not repo:
            return

        if select_branch:
            self.show_branches_panel(repo, partial(self.harvest, repo))
        else:
            self.harvest(repo)

    def harvest(self, repo, branch=None):
        def on_done(into_branch):
            into_branch = into_branch.strip()
            if into_branch:
                out = self.legit_string(['harvest', branch, into_branch], cwd=repo)
                panel = self.window.get_output_panel('legit-harvest')
                panel.run_command('git_panel_write', {'content': out})
                self.window.run_command('show_panel', {'panel': 'output.legit-harvest'})

        self.show_branches_panel(repo, on_done)


class LegitSproutCommand(LegitWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self, select_branch=False):
        repo = self.get_repo()
        if not repo:
            return

        if select_branch:
            self.show_branches_panel(repo, partial(self.sprout, repo))
        else:
            self.sprout(repo)

    def sprout(self, repo, branch=None):
        def on_done(new_branch):
            new_branch = new_branch.strip()
            if new_branch:
                out = self.legit_string(['sprout', branch, new_branch], cwd=repo)
                panel = self.window.get_output_panel('legit-sprout')
                panel.run_command('git_panel_write', {'content': out})
                self.window.run_command('show_panel', {'panel': 'output.legit-sprout'})

        self.window.show_input_panel('New branch:', '', on_done, noop, noop)


class LegitGraftCommand(LegitWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        self.show_branches_panel(repo, partial(self.graft, repo), filter=('unpublished',))

    def graft(self, repo, branch):
        out = self.legit_string(['graft', branch], cwd=repo)
        panel = self.window.get_output_panel('legit-graft')
        panel.run_command('git_panel_write', {'content': out})
        self.window.run_command('show_panel', {'panel': 'output.legit-graft'})


class LegitBranchesCommand(LegitWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        self.show_branches_panel(repo, noop)
