# coding: utf-8
from sublime_plugin import WindowCommand

from .util import noop, find_view_by_settings, ensure_writeable, write_view
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
        repo = self.get_repo(self.window)
        show = self.get_show(obj)

        if show and repo:
            title = GIT_SHOW_TITLE_PREFIX + obj
            view = find_view_by_settings(self.window, git_view='show', git_repo=repo, git_show=obj)
            if not view:
                view = self.window.new_file()
                view.set_name(title)
                view.set_scratch(True)
                view.set_read_only(True)
                view.set_syntax_file(GIT_SHOW_SYNTAX)

                view.settings().set('git_view', 'show')
                view.settings().set('git_repo', repo)
                view.settings().set('git_show', obj)

            with ensure_writeable(view):
                write_view(view, show)
