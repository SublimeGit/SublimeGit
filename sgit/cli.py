# coding: utf-8
from sublime_plugin import WindowCommand

from .util import noop
from .cmd import GitCmd


class GitCliCommand(WindowCommand, GitCmd):

    def run(self, command=None):
        cmd = "fake"

        def on_done(args):
            if args:
                print "%s %s" % (cmd, args)

        self.window.show_input_panel(cmd, '', on_done, noop, noop)


class GitCliAsyncCommand(WindowCommand, GitCmd):

    def run(self, command=None):
        cmd = "fake"

        def on_done(args):
            if args:
                print args

        self.window.show_input_panel(cmd, '', on_done, noop, noop)
