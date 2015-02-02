# coding: utf-8
import re
from functools import partial

import sublime
from sublime_plugin import WindowCommand, TextCommand, EventListener

from .util import find_view_by_settings, get_setting
from .cmd import GitCmd
from .helpers import GitDiffHelper, GitErrorHelper, GitStatusHelper


RE_DIFF_HEAD = re.compile(r'(---|\+\+\+){3} (a|b)/(dev/null)?')


GIT_DIFF_TITLE = '*git-diff*'
GIT_DIFF_TITLE_PREFIX = GIT_DIFF_TITLE + ': '
GIT_DIFF_CACHED_TITLE = '*git-diff-cached*'
GIT_DIFF_CACHED_TITLE_PREFIX = GIT_DIFF_CACHED_TITLE + ': '

GIT_DIFF_CLEAN = "Nothing to stage (no difference between working tree and index)"
GIT_DIFF_CLEAN_CACHED = "Nothing to unstage (no changes in index)"

GIT_DIFF_VIEW_SYNTAX = 'Packages/SublimeGit/syntax/SublimeGit Diff.tmLanguage'

GIT_DIFF_UNSTAGE_ERROR = "Cannot unstage hunks which have not been staged."
GIT_DIFF_STAGE_ERROR = "Cannot stage hunks which are already staged."


class GitDiffCommand(WindowCommand, GitCmd):
    """
    Shows a diff of the entire repository in a diff view.

    This diff is between the worktree and the index. Thus, these are the
    changes that you could ask git to add to the next commit.

    For diff on a single file, either use the **Git: Quick Status** command,
    or press ``d`` when the cursor is on a file in the status view.
    """

    def run(self, repo=None, path=None, cached=False):
        repo = repo or self.get_repo()
        if not repo:
            return

        path = path or repo

        title = self.get_view_title(path, cached)
        git_view = 'diff%s' % ('-cached' if cached else '')

        view = find_view_by_settings(self.window, git_view=git_view, git_repo=repo, git_diff_path=path)
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
            view.settings().set('git_diff_unified', 3)

        self.window.focus_view(view)
        view.run_command('git_diff_refresh', {'path': path, 'cached': cached, 'run_move': True})

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


class GitDiffCurrentFileCommand(GitCmd, GitStatusHelper, TextCommand):
    """
    Shows a diff for the current file, if possible.
    """

    def run(self, edit, cached=False):
        # check if file is saved
        filename = self.view.file_name()
        if not filename:
            sublime.error_message('Cannot do git-diff on unsaved files.')
            return

        repo = self.get_repo()
        if not repo:
            return

        # check if file is known to git
        in_git = self.file_in_git(repo, filename)
        if not in_git:
            sublime.error_message('The file %s is not tracked by git.' % filename.replace(repo, '').lstrip('/'))
            return

        self.view.window().run_command('git_diff', {'repo': repo, 'path': filename, 'cached': cached})


class GitDiffCachedCurrentFileCommand(GitDiffCurrentFileCommand):
    """
    Shows a cached diff for the current file, if possible.
    """

    def run(self, edit):
        super(GitDiffCachedCurrentFileCommand, self).run(edit, cached=True)


class GitDiffTextCmd(GitCmd, GitDiffHelper):

    def move_to_point(self, point):
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(point))
        if not self.view.visible_region().contains(point):
            view = self.view
            sublime.set_timeout(partial(view.show, point, True), 50)

    def parse_diff(self):
        sections = []
        state = None

        prev_file = None
        current_file = {}
        current_hunks = []

        prev_hunk = None
        current_hunk = None

        for line in self.view.lines(sublime.Region(0, self.view.size())):
            linetext = self.view.substr(line)

            if linetext.startswith('diff --git'):
                state = 'header'
                # new file starts
                if prev_file != line:
                    if prev_file is not None:
                        if current_hunk:
                            current_hunks.append(current_hunk)
                        sections.append((current_file, current_hunks))
                    prev_file = line
                    prev_hunk = None

                current_file = line
                current_hunks = []
            elif state == 'header' and RE_DIFF_HEAD.match(linetext):
                current_file = current_file.cover(line)
            elif linetext.startswith('@@'):
                state = 'hunk'
                # new hunk starts
                if prev_hunk != line:
                    if prev_hunk is not None:
                        current_hunks.append(current_hunk)
                    prev_hunk = line

                current_hunk = line
            elif state == 'hunk' and linetext[0] in (' ', '-', '+'):
                current_hunk = current_hunk.cover(line)
            elif state == 'header':
                current_file = current_file.cover(line)

        if current_file and current_hunk:
            current_hunks.append(current_hunk)
            sections.append((current_file, current_hunks))
        return sections

    def build_lookup(self, parsed_diff):
        lookup = []
        for header, hunks in parsed_diff:
            for h in hunks:
                lookup.append((h, header))
        return lookup

    def get_hunks_from_selection(self, selection):
        if not selection:
            return None
        # parse the diff view
        diffspec = self.parse_diff()
        lookup = self.build_lookup(diffspec)

        # find the applicable hunks
        hunks = {}
        for s in selection:
            for hunk, header in lookup:
                if s.intersects(hunk) or hunk.contains(s) or (s.begin() == self.view.size() and hunk.contains(s.begin() - 1)):
                    hunks.setdefault((header.begin(), header.end()), []).append(hunk)

        return hunks

    def create_patch(self, selected_hunks):
        patch = []
        for (hstart, hend), hunks in selected_hunks.items():
            header = sublime.Region(hstart, hend)
            for head in self.view.lines(header):
                headline = self.view.substr(head)
                if headline.startswith('---') or headline.startswith('+++'):
                    patch.append("%s\n" % headline.strip())
                else:
                    patch.append("%s\n" % headline)
            for h in hunks:
                patch.append(self.view.substr(self.view.full_line(h)))
        return "".join(patch)


class GitDiffRefreshCommand(TextCommand, GitDiffTextCmd):

    def is_visible(self):
        return False

    def run(self, edit, path=None, cached=False, run_move=False):
        path = path if path else self.view.settings().get('git_diff_path')
        cached = cached if cached else self.view.settings().get('git_diff_cached')
        unified = self.view.settings().get('git_diff_unified', 3)
        repo = self.view.settings().get('git_repo')

        if path is None or cached is None:
            return

        point = self.view.sel()[0].begin() if self.view.sel() else 0
        row, col = self.view.rowcol(point)

        diff = self.get_diff(repo, path, cached, unified=unified)
        clean = False
        if not diff:
            diff = GIT_DIFF_CLEAN_CACHED if cached else GIT_DIFF_CLEAN
            clean = True

        self.view.settings().set('git_diff_clean', clean)
        self.view.set_read_only(False)
        self.view.replace(edit, sublime.Region(0, self.view.size()), diff)
        self.view.set_read_only(True)

        if run_move:
            self.view.run_command('git_diff_move')
        else:
            row_begin = self.view.text_point(row, 0)
            line = self.view.line(row_begin)
            point = self.view.text_point(row, min(col, (line.end() - line.begin())))
            self.move_to_point(point)


class GitDiffEventListener(EventListener):

    def on_activated(self, view):
        if view.settings().get('git_view') in ('diff', 'diff-cached') and get_setting('git_update_diff_on_focus', True):
            view.run_command('git_diff_refresh')


class GitDiffChangeHunkSizeCommand(TextCommand):

    def is_visible(self):
        return False

    def run(self, edit, action='increase'):
        unified = self.view.settings().get('git_diff_unified', 3)
        if action == 'increase':
            self.view.settings().set('git_diff_unified', unified + 1)
        else:
            self.view.settings().set('git_diff_unified', max(1, unified - 1))
        self.view.run_command('git_diff_refresh')


class GitDiffMoveCommand(TextCommand, GitDiffTextCmd):

    def is_visible(self):
        return False

    def run(self, edit, item='hunk', which=0, start=None):
        # There is nothing to do here
        if self.view.settings().get('git_diff_clean') is True:
            return

        if item not in ('hunk', 'file'):
            return
        try:
            which = int(which)
        except ValueError:
            if which not in ('first', 'last', 'next', 'prev'):
                return

        if start is not None:
            start = int(start)
        elif self.view.sel():
            start = self.view.sel()[0].begin()
        else:
            start = 0

        file_lookup = self.parse_diff()
        hunk_lookup = self.build_lookup(file_lookup)
        if not hunk_lookup:
            return

        goto = None
        if which == 'first':
            goto, _ = hunk_lookup[0]
        elif which == 'last':
            goto, _ = hunk_lookup[-1]
        elif which == 'next':
            if item == 'hunk':
                next_hunks = [(h, f) for h, f in hunk_lookup if h.begin() > start]
                goto, _ = next_hunks[0] if next_hunks else hunk_lookup[-1]
            else:
                next_files = [(f, h) for f, h in file_lookup if f.begin() > start]
                goto, _ = next_files[0] if next_files else file_lookup[-1]
        elif which == 'prev':
            if item == 'hunk':
                prev_hunks = [(h, f) for h, f in hunk_lookup if h.end() < start]
                goto, _ = prev_hunks[-1] if prev_hunks else hunk_lookup[0]
            else:
                prev_files = [(f, h) for f, h in file_lookup if h[-1].end() < start]
                goto, _ = prev_files[-1] if prev_files else file_lookup[0]
        else:
            if item == 'hunk':
                goto, _ = hunk_lookup[max(0, which)] if which < len(hunk_lookup) else hunk_lookup[-1]
            else:
                goto, _ = file_lookup[max(0, which)] if which < len(file_lookup) else file_lookup[-1]

        if goto:
            self.move_to_point(goto.begin())


class GitDiffStageUnstageHunkCommand(GitDiffTextCmd, GitErrorHelper, TextCommand):

    def is_visible(self):
        return False

    def run(self, edit, reverse=False):
        repo = self.view.settings().get('git_repo')

        # we can't unstage stuff hasn't been staged
        if self.view.settings().get('git_diff_cached') is not reverse:
            if reverse:
                sublime.error_message(GIT_DIFF_UNSTAGE_ERROR)
            else:
                sublime.error_message(GIT_DIFF_STAGE_ERROR)
            return

        # There is nothing to do here
        if self.view.settings().get('git_diff_clean') is True:
            return

        hunks = self.get_hunks_from_selection(self.view.sel())
        if hunks:
            patch = self.create_patch(hunks)
            cmd = ['apply', '--ignore-whitespace', '--cached', '--reverse' if reverse else None, '-']
            exit, stdout, stderr = self.git(cmd, stdin=patch, cwd=repo)
            if exit != 0:
                sublime.error_message(self.format_error_message(stderr))
            self.view.run_command('git_diff_refresh')
