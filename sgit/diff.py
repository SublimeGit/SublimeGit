# coding: utf-8
import sublime
from sublime_plugin import WindowCommand, TextCommand

from .util import find_view_by_settings
from .cmd import GitCmd
from .helpers import GitDiffHelper


GIT_DIFF_TITLE = '*git-diff*'
GIT_DIFF_TITLE_PREFIX = GIT_DIFF_TITLE + ': '
GIT_DIFF_CACHED_TITLE = '*git-diff-cached*'
GIT_DIFF_CACHED_TITLE_PREFIX = GIT_DIFF_CACHED_TITLE + ': '

GIT_DIFF_VIEW_SYNTAX = 'Packages/SublimeGit/SublimeGit Diff.tmLanguage'


class GitDiffCommand(WindowCommand, GitCmd):
    """
    Shows a diff of the entire repository in a diff view.

    This diff is between the worktree and the index. Thus, these are the
    changes that you could ask git to add to the next commit.

    For diff on a single file, either use the **Git: Quick Status** command,
    or press **d** when the cursor is on a file in the status view.
    """

    def run(self, path=None, cached=False):
        repo = self.get_repo(self.window)

        if repo:
            if path is None:
                path = repo
            title = self.get_view_title(path, cached)
            git_view = 'diff%s' % ('-cached' if cached else '')

            view = find_view_by_settings(self.window, git_view=git_view, git_repo=repo, git_diff=path)
            if not view:
                view = self.window.new_file()
                view.set_name(title)
                view.set_syntax_file(GIT_DIFF_VIEW_SYNTAX)
                view.set_scratch(True)
                view.set_read_only(True)

                view.settings().set('git_view', git_view)
                view.settings().set('git_repo', repo)
                view.settings().set('git_diff_path', path)
                view.settings().set('git_diff_cached', cached)

            view.run_command('git_diff_refresh', {'path': path, 'cached': cached})

    def get_view_title(self, path=None, cached=False):
        if cached:
            return GIT_DIFF_CACHED_TITLE_PREFIX + path if path else GIT_DIFF_CACHED_TITLE
        else:
            return GIT_DIFF_TITLE_PREFIX + path if path else GIT_DIFF_TITLE


class GitDiffCachedCommand(GitDiffCommand):
    """
    Shows the cached diff for the entire repository in a diff view.

    The difference between this command and the **Git: Diff** command is
    that this command shows the difference between the staged changes (the changes
    in the index), and the HEAD. I.e. these are changes which you could tell git
    to unstage.

    For diff on a single file, either use the **Git: Quick Status** command,
    or press **d** when the cursor is on a file in the status view.
    """

    def run(self, path=None):
        super(GitDiffCachedCommand, self).run(path=path, cached=True)


class GitDiffRefreshCommand(TextCommand, GitCmd, GitDiffHelper):

    def run(self, edit, path=None, cached=False):
        path = path if path else self.view.settings().get('git_diff_path')
        cached = cached if cached else self.view.settings().get('git_diff_cached')

        if path is None or cached is None:
            return

        diff = self.get_diff(path, cached)
        if diff:
            self.view.set_read_only(False)
            if self.view.size() > 0:
                self.view.erase(edit, sublime.Region(0, self.view.size()))
            self.view.insert(edit, 0, diff)
            self.view.set_read_only(True)
