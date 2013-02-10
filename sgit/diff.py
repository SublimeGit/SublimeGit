# coding: utf-8
from sublime_plugin import WindowCommand

from .util import find_or_create_view, write_view, ensure_writeable
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

        if diff:
            title = self.get_view_title(path, cached)
            view = find_or_create_view(self.window, title,
                                        syntax=GIT_DIFF_VIEW_SYNTAX,
                                        scratch=True,
                                        read_only=True)
            with ensure_writeable(view):
                write_view(view, diff)

    def get_view_title(self, path=None, cached=False):
        if cached:
            return GIT_DIFF_CACHED_TITLE_PREFIX + path if path else GIT_DIFF_CACHED_TITLE
        else:
            return GIT_DIFF_TITLE_PREFIX + path if path else GIT_DIFF_TITLE
