# coding: utf-8
import re
from datetime import datetime
import sublime
from sublime_plugin import TextCommand, WindowCommand, EventListener

from .util import find_view_by_settings, get_setting
from .cmd import GitCmd
from .helpers import GitStatusHelper, GitRepoHelper


GIT_BLAME_TITLE_PREFIX = '*git-blame*: '
GIT_BLAME_SYNTAX = 'Packages/SublimeGit/syntax/SublimeGit Blame.tmLanguage'


class GitBlameCache(object):
    commits = {}
    lines = {}


class GitBlameCommand(WindowCommand, GitCmd, GitStatusHelper):
    """
    Run git blame on the current file.

    This will bring up a new window with the blame information to
    the left of the file contents, on a per-line basis. Lines which
    are selected when executing the commands will be marked with a dot
    in the gutter. When placing the cursor on a line, the summary of
    the commit will be shown in the status bar.

    If the file has not been saved to the filesystem, or the file is
    not tracked by git, it's not possible to blame, and an error
    will be shown.

    To navigate further into the blame information, a couple of keyboard
    shortcuts are available:

    * ``enter``: Show the commit in a new window (like Git: Show).
    * ``b``: Open a new blame starting at the given commit.

    .. note::
        These keyboard shortcuts support multiple selection, so you
        can potentially open **a lot** of tabs. If your action will
        open more than 5 tabs, you will get a warning asking if you
        want to continue. You can turn this warning off with the
        **git_blame_warn_multiple_tabs** setting.

    :setting git_blame_warn_multiple_tabs: If set to ``true``, SublimeGit
        will give you a warning when your action from a blame view will
        open more than 5 tabs. Set to ``false`` to turn this warning off.

    """

    def run(self, repo=None, filename=None, revision=None):
        # check if file is saved
        filename = filename if filename else self.window.active_view().file_name()
        if not filename:
            sublime.error_message('Cannot do git-blame on unsaved files.')
            return

        repo = repo or self.get_repo()
        if not repo:
            return

        # check if file is known to git
        in_git = self.file_in_git(repo, filename)
        if not in_git:
            sublime.error_message('The file %s is not tracked by git.' % filename)
            return

        # figure out where we are in the file
        rows = []
        sel = self.window.active_view().sel()
        if sel:
            for s in sel:
                for l in self.window.active_view().lines(s):
                    row, _ = self.window.active_view().rowcol(l.begin())
                    rows.append(row)

        title = GIT_BLAME_TITLE_PREFIX + filename.replace(repo, '').lstrip('/\\')
        if revision:
            title = '%s @ %s' % (title, revision[:7])
        view = find_view_by_settings(self.window, git_view='blame', git_repo=repo,
                                     git_blame_file=filename, git_blame_rev=revision)

        if view is None:
            view = self.window.new_file()
            view.set_name(title)
            view.set_scratch(True)
            view.set_read_only(True)
            view.set_syntax_file(GIT_BLAME_SYNTAX)

            view.settings().set('word_wrap', False)
            view.settings().set('git_view', 'blame')
            view.settings().set('git_repo', repo)
            view.settings().set('git_blame_file', filename)
            view.settings().set('git_blame_rev', revision)

        view.run_command('git_blame_refresh', {'filename': filename, 'revision': revision, 'rows': rows})


class GitBlameRefreshCommand(TextCommand, GitCmd):

    HEADER_RE = re.compile(r'^(?P<sha>[0-9a-f]{40}) (\d+) (\d+) ?(\d+)?$')

    def parse_commit_line(self, commitline):
        parts = commitline.split(' ', 1)
        if len(parts) == 2:
            fieldname, value = parts
        else:
            fieldname, value = parts[0], ''
        value = value.strip()
        if fieldname in ('committer-time', 'author-time'):
            value = int(value)
        elif fieldname in ('committer-mail', 'author-mail'):
            value = value.strip('<>')
        elif fieldname in ('previous',):
            sha, filename = value.split(' ', 1)
            value = {'commit': sha, 'file': filename}
        elif fieldname in ('boundary',):
            value = True
        return fieldname, value

    def get_blame(self, repo, filename, revision=None):
        data = self.git_lines(['blame', '--porcelain', revision if revision else None, '--', filename], cwd=repo)

        commits = {}
        lines = []

        current_commit = None
        for l, item in enumerate(data, start=1):
            try:
                headermatch = self.HEADER_RE.match(item)
                if headermatch:
                    sha = headermatch.group('sha')
                    commits.setdefault(sha, {})['sha'] = sha
                    current_commit = sha
                elif item[0] == '\t':
                    lines.append((current_commit, item[1:]))
                else:
                    field, val = self.parse_commit_line(item)
                    commits.setdefault(current_commit, {})[field] = val
            except Exception as e:
                sublime.error_message('Error parsing git blame output: %s', e)
                return {}, []

        abbrev_length = 7
        while abbrev_length < 40:
            abbrevs = [c['sha'][:abbrev_length] for c in commits.values()]
            if len(abbrevs) == len(set(abbrevs)):
                break
            abbrev_length += 1

        for k in commits:
            commits[k]['abbrev'] = commits[k]['sha'][:abbrev_length]

        return commits, lines

    def get_commit_date(self, commit):
        return datetime.fromtimestamp(commit.get('author-time'))

    def format_blame(self, commits, lines):
        content = []
        template = u"{boundary}{sha} {file}({author} {date}) {line}"

        files = set(c.get('filename') for _, c in commits.items() if c.get('filename'))
        max_file = max(len(f) for f in files)
        max_name = max(len(c.get('author', '')) for _, c in commits.items())
        boundaries = any('boundary' in c for _, c in commits.items())

        for sha, line in lines:
            commit = commits.get(sha)
            date = self.get_commit_date(commit)
            c = template.format(
                boundary='^' if 'boundary' in commit else (' ' if boundaries else ''),
                sha=commit.get('abbrev'),
                file=commit.get('filename').ljust(max_file + 1) if len(files) > 1 else '',
                author=commit.get('author', '').ljust(max_name + 1, ' '),
                date=date.strftime("%a %b %d %H:%M:%S %Y"),
                line=line
            )
            content.append(c)
        return "\n".join(content)

    def is_visible(self):
        return False

    def run(self, edit, filename=None, revision=None, rows=None):
        filename = filename or self.view.settings().get('git_blame_file')
        revision = revision or self.view.settings().get('git_blame_rev')
        repo = self.view.settings().get('git_repo')

        commits, lines = self.get_blame(repo, filename, revision)
        if not commits or not lines:
            return
        GitBlameCache.commits[self.view.id()] = commits
        GitBlameCache.lines[self.view.id()] = lines

        blame = self.format_blame(commits, lines)

        if blame:
            # write blame to file
            self.view.set_read_only(False)
            if self.view.size() > 0:
                self.view.erase(edit, sublime.Region(0, self.view.size()))
            self.view.insert(edit, 0, blame)
            self.view.set_read_only(True)

            # mark lines selected
            if rows:
                lines = []
                for row in rows:
                    lines.append(self.view.line(self.view.text_point(row, 0)))

                # add dots in the sidebar
                self.view.add_regions('git-blame.lines', lines, 'git-blame.selection', 'dot', sublime.HIDDEN)

            # place cursor on same line as in old selection
            row = rows[0] if rows else 0
            point = self.view.text_point(row, 0)
            self.view.sel().clear()
            self.view.sel().add(sublime.Region(point))
            if not self.view.visible_region().contains(point):
                sublime.set_timeout(lambda: self.view.show_at_center(point), 50)


class GitBlameEventListener(EventListener):
    _lpop = False

    def on_selection_modified(self, view):
        if view.settings().get('git_view') == 'blame':
            commits = GitBlameCache.commits.get(view.id())
            lines = GitBlameCache.lines.get(view.id())

            if lines and commits:
                row, col = view.rowcol(view.sel()[0].begin())
                sha, line = lines[row]
                commit = commits.get(sha)
                if commit:
                    sublime.status_message(commit.get('summary'))


class GitBlameTextCommand(GitRepoHelper):

    def commits_from_selection(self):
        lines = GitBlameCache.lines.get(self.view.id())
        commits = GitBlameCache.commits.get(self.view.id())

        if not lines or not commits:
            return

        linesets = [self.view.lines(s) for s in self.view.sel()]
        linenums = set()
        for lineset in linesets:
            for l in lineset:
                row, _ = self.view.rowcol(l.begin())
                linenums.add(row)

        if not linenums:
            return

        selected_commits = {}
        for n in linenums:
            sha, _ = lines[n]
            if sha not in selected_commits and set(sha) != set(['0']):
                selected_commits[sha] = commits.get(sha)
        return selected_commits

    def validate_num_commits(self, commits):
        if commits is None:
            return False

        if len(commits) == 0:
            sublime.error_message('No commits selected.')
            return False

        if len(commits) > 5 and get_setting('git_blame_warn_multiple_tabs', True):
            if not sublime.ok_cancel_dialog('This will open %s tabs. Are you sure you want to continue?' % len(commits), 'Open tabs'):
                return False

        return True


class GitBlameShowCommand(TextCommand, GitBlameTextCommand):

    def is_visible(self):
        return False

    def run(self, edit):
        commits = self.commits_from_selection()
        valid = self.validate_num_commits(commits)

        if not valid:
            return

        repo = self.get_repo()
        if not repo:
            return

        window = self.view.window()
        for sha, _ in commits.items():
            window.run_command('git_show', {'repo': repo, 'obj': sha})


class GitBlameBlameCommand(TextCommand, GitBlameTextCommand):

    def is_visible(self):
        return False

    def run(self, edit):
        commits = self.commits_from_selection()
        valid = self.validate_num_commits(commits)

        if not valid:
            return

        repo = self.get_repo()
        if not repo:
            return

        window = self.view.window()
        for sha, c in commits.items():
            filename = c.get('filename', None)
            window.run_command('git_blame', {'repo': repo, 'filename': filename, 'revision': sha})
