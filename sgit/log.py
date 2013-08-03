# coding: utf-8
#import sublime
from sublime_plugin import WindowCommand, TextCommand

from .util import noop
from .cmd import GitCmd
from .helpers import GitLogHelper


GIT_LOG_FORMAT = '--format=%s%n%H by %an <%aE>%n%ar (%ad)'


class GitLogCommand(WindowCommand, GitCmd):
    """
    Documentation coming soon.
    """

    def run(self):
        self.window.run_command('git_quick_log')


class GitQuickLogCommand(WindowCommand, GitCmd, GitLogHelper):
    """
    Documentation coming soon.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        log = self.get_quick_log(repo)
        hashes, choices = self.format_quick_log(log)

        def on_done(idx):
            if idx == -1:
                return
            commit = hashes[idx]
            self.window.run_command('git_show', {'obj': commit, 'repo': repo})

        self.window.show_quick_panel(choices, on_done)


class GitQuickLogCurrentFileCommand(TextCommand, GitCmd, GitLogHelper):
    """
    Documentation coming soon.
    """

    def run(self, edit):
        filename = self.view.file_name()
        if not filename:
            self.window.show_quick_panel(['No log for file'], noop)

        repo = self.get_repo()
        if not repo:
            return

        log = self.get_quick_log(repo, path=filename, follow=True)
        hashes, choices = self.format_quick_log(log)

        def on_done(idx):
            if idx == -1:
                return
            commit = hashes[idx]
            self.view.window().run_command('git_show', {'obj': commit, 'repo': repo})

        self.view.window().show_quick_panel(choices, on_done)
