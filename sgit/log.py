# coding: utf-8
#import sublime
from sublime_plugin import WindowCommand, TextCommand

from .util import noop
from .cmd import GitCmd
from .helpers import GitLogHelper


GIT_LOG_FORMAT = '--format=%s%n%H by %an <%aE>%n%ar (%ad)'


class GitLogCommand(WindowCommand, GitCmd):

    def run(self):
        #print self.git_string(['log', '--graph', "--pretty=format:%Cred%h%Creset %an: %s - %Creset %C(yellow)%d%Creset %Cgreen(%cr)%Creset", '--abbrev-commit', '--date=relative'])
        log = self.git_string(['log', '-z', '--date=local', GIT_LOG_FORMAT])
        lines = [l.split('\n') for l in log.split(u"\u0000") if l != '']
        self.window.show_quick_panel(lines, noop)


class GitQuickLogCommand(WindowCommand, GitCmd, GitLogHelper):

    def run(self):
        hashes, choices = self.format_quick_log()

        def on_done(idx):
            if idx == -1:
                return
            commit = hashes[idx]
            self.window.run_command('git_show', {'obj': commit})

        self.window.show_quick_panel(choices, on_done)


class GitQuickLogCurrentFileCommand(TextCommand, GitCmd, GitLogHelper):

    def run(self, edit):
        filename = self.view.file_name()
        if not filename:
            self.window.show_quick_panel(['No log for file'], noop)

        hashes, choices = self.format_quick_log(path=filename, follow=True)

        def on_done(idx):
            if idx == -1:
                return
            commit = hashes[idx]
            self.view.window().run_command('git_show', {'obj': commit})

        self.view.window().show_quick_panel(choices, on_done)
