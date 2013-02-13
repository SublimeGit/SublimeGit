# coding: utf-8
from sublime_plugin import WindowCommand

from .util import find_view_by_settings, write_view, ensure_writeable
from .cmd import GitCmd
from .helpers import GitDiffHelper


GIT_DIFF_TITLE = '*git-diff*'
GIT_DIFF_TITLE_PREFIX = GIT_DIFF_TITLE + ': '
GIT_DIFF_CACHED_TITLE = '*git-diff--cached*'
GIT_DIFF_CACHED_TITLE_PREFIX = GIT_DIFF_CACHED_TITLE + ': '

GIT_DIFF_VIEW_SYNTAX = 'Packages/SublimeGit/SublimeGit Diff.tmLanguage'


class GitDiffCommand(WindowCommand, GitCmd, GitDiffHelper):

    def run(self, path=None, cached=False):
        diff = self.get_diff(path, cached)
        repo = self.get_repo(self.window)

        if diff:
            title = self.get_view_title(path, cached)
            git_view = 'diff' + '-cached' if cached else ''

            view = find_view_by_settings(self.window, git_view=git_view, git_repo=repo, git_diff=path)
            if not view:
                view = self.window.new_file()
                view.set_name(title)
                view.set_syntax_file(GIT_DIFF_VIEW_SYNTAX)
                view.set_scratch(True)
                view.set_read_only(True)

                view.settings().set('git_view', git_view)
                view.settings().set('git_repo', repo)
                view.settings().set('git_diff', path)

            with ensure_writeable(view):
                write_view(view, diff)

    def get_view_title(self, path=None, cached=False):
        if cached:
            return GIT_DIFF_CACHED_TITLE_PREFIX + path if path else GIT_DIFF_CACHED_TITLE
        else:
            return GIT_DIFF_TITLE_PREFIX + path if path else GIT_DIFF_TITLE
