# coding: utf-8
import re
from functools import partial

import sublime
from sublime_plugin import WindowCommand, TextCommand

from .util import find_view_by_settings
from .cmd import GitCmd
from .helpers import GitDiffHelper


RE_DIFF_HEAD = re.compile(r'(---|\+\+\+){3} (a|b)/(dev/null)?')


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
    or press ``d`` when the cursor is on a file in the status view.
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
                view.settings().set('git_diff_unified', 3)

            view.run_command('git_diff_refresh', {'path': path, 'cached': cached, 'goto': 'hunk:first'})

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


class GitDiffTextCmd(GitCmd, GitDiffHelper):

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
        for s in self.view.sel():
            for hunk, header in lookup:
                print s, hunk, s.intersects(hunk), hunk.contains(s)
                if s.intersects(hunk) or hunk.contains(s):
                    hunks.setdefault(header, []).append(hunk)

        return hunks

    def create_patch(self, selected_hunks):
        patch = []
        for header, hunks in selected_hunks.items():
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

    def run(self, edit, path=None, cached=False, goto=None, start=None):
        path = path if path else self.view.settings().get('git_diff_path')
        cached = cached if cached else self.view.settings().get('git_diff_cached')
        unified = self.view.settings().get('git_diff_unified', 3)

        if path is None or cached is None:
            return

        if start is None:
            start = self.view.sel()[0].begin() if self.view.sel() else None

        diff = self.get_diff(path, cached, unified=unified)
        self.view.set_read_only(False)
        if self.view.size() > 0:
            self.view.erase(edit, sublime.Region(0, self.view.size()))
        self.view.insert(edit, 0, diff)
        self.view.set_read_only(True)

        if goto:
            self.view.run_command('git_diff_move', {'start': start, 'goto': goto})


class GitDiffChangeHunkSizeCommand(TextCommand):
    """
    Documentation coming soon.
    """

    def run(self, edit, action='increase'):
        unified = self.view.settings().get('git_diff_unified', 3)
        if action == 'increase':
            self.view.settings().set('git_diff_unified', unified + 1)
        else:
            self.view.settings().set('git_diff_unified', max(1, unified - 1))
        point = self.view.sel()[0].begin()
        self.view.run_command('git_diff_refresh', {'start': point, 'goto': 'hunk:first'})


class GitDiffMoveCommand(TextCommand, GitDiffTextCmd):

    def is_visible(self):
        return False

    def parse_goto(self, goto):
        parts = goto.split(':')
        if len(parts) != 2:
            return None
        item, direction = parts
        if item not in ('hunk', 'file'):
            return None
        if direction not in ('next', 'prev', 'first'):
            return None
        return (item, direction)

    def move_to_point(self, point):
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(point))
        if not self.view.visible_region().contains(point):
            view = self.view
            sublime.set_timeout(partial(view.show, point, True), 50)

    def run(self, edit, goto='hunk:next', start=None):
        goto = self.parse_goto(goto)
        if not goto:
            return
        item, direction = goto

        print "preif start", type(start)

        if start is not None:
            point = int(start)
        elif self.view.sel():
            point = self.view.sel()[0].begin()
        else:
            point = 0

        print "postif", type(point)

        if point is not None:
            lookup = self.build_lookup(self.parse_diff())

            goto_lookup = None
            if direction == 'first':
                goto_lookup = lookup[0]
            else:
                for i in range(len(lookup)):
                    hunk, header = lookup[i]
                    if hunk.contains(point) or header.contains(point):
                        if direction == 'prev':
                            goto_lookup = lookup[i-1] if i > 0 else lookup[0]
                        else:
                            if item == 'hunk' and header.contains(point):
                                goto_lookup = lookup[i]
                            else:
                                goto_lookup = lookup[i+1] if i+1 < len(lookup) else lookup[-1]
                        break

                if not goto_lookup:
                    goto_lookup = lookup[-1]

            print goto_lookup

            if goto_lookup:
                goto_hunk, goto_header = goto_lookup
                if item == 'file':
                    self.move_to_point(goto_header.begin())
                else:
                    self.move_to_point(goto_hunk.begin())


class GitDiffUnstageHunkCommand(TextCommand, GitDiffTextCmd):
    """
    Documentation coming soon.
    """

    def run(self, edit):
        # we can't unstage stuff hasn't been staged
        if self.view.settings().get('git_diff_cached') is False:
            return

        hunks = self.get_hunks_from_selection(self.view.sel())
        if hunks:
            patch = self.create_patch(hunks)
            exit, stdout = self.git(['apply', '--ignore-whitespace', '--cached', '--reverse', '-'], stdin=patch)
            self.view.run_command('git_diff_refresh', {'goto': 'hunk:next'})


class GitDiffStageHunkCommand(TextCommand, GitDiffTextCmd):
    """
    Documentation coming soon.
    """

    def run(self, edit):
        # we can't stage stuff that's already staged
        if self.view.settings().get('git_diff_cached') is True:
            return

        hunks = self.get_hunks_from_selection(self.view.sel())
        if hunks:
            patch = self.create_patch(hunks)
            exit, stdout = self.git(['apply', '--ignore-whitespace', '--cached', '-'], stdin=patch)
            self.view.run_command('git_diff_refresh', {'goto': 'hunk:next'})
