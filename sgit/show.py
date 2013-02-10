# coding: utf-8
from sublime_plugin import WindowCommand

from .util import noop, find_or_create_view, ensure_writeable, write_view
from .cmd import GitCmd
from .helpers import GitShowHelper


GIT_SHOW_TITLE_PREFIX = '*git-show*: '
GIT_SHOW_SYNTAX = 'Packages/SublimeGit/SublimeGit Show.tmLanguage'


class GitShowCommand(WindowCommand, GitCmd, GitShowHelper):

    def run(self, obj=None):
        if not obj:
            self.window.show_input_panel('Object:', '', self.show, noop, noop)
        else:
            self.show(obj)

    def show(self, obj):
        show = self.get_show(obj)

        if show:
            title = GIT_SHOW_TITLE_PREFIX + obj
            view = find_or_create_view(self.window, title,
                                        syntax=GIT_SHOW_SYNTAX,
                                        scratch=True,
                                        read_only=True)
            with ensure_writeable(view):
                write_view(view, show)
