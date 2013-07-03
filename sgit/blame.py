# coding: utf-8
import re
from datetime import datetime
import sublime
from sublime_plugin import TextCommand

from .util import find_view_by_settings
from .cmd import GitCmd


GIT_BLAME_TITLE_PREFIX = '*git-blame*: '
GIT_BLAME_SYNTAX = 'Packages/SublimeGit/SublimeGit Blame.tmLanguage'


class GitBlameCommand(TextCommand, GitCmd):
    """
    Documentation coming soon.
    """

    def run(self, edit):
        # check if file is saved
        filename = self.view.file_name()
        if not filename:
            sublime.error_message('Cannot do git-blame on unsaved files.')
            return

        # get newest revision of file
        # if revision is missing, show error message
        rev = None

        repo = self.get_repo(self.view.window())
        if repo:
            title = GIT_BLAME_TITLE_PREFIX + filename.replace(repo, '').lstrip('/\\')
            view = find_view_by_settings(self.view.window(), git_view='blame', git_repo=repo,
                                         git_blame_file=filename, git_blame_rev=rev)

            if not view:
                view = self.view.window().new_file()
                view.set_name(title)
                view.set_scratch(True)
                view.set_read_only(True)
                view.set_syntax_file(GIT_BLAME_SYNTAX)

                view.settings().set('word_wrap', False)
                view.settings().set('git_view', 'blame')
                view.settings().set('git_repo', repo)
                view.settings().set('git_blame_file', filename)
                view.settings().set('git_blame_rev', rev)

            view.run_command('git_blame_refresh', {'filename': filename, 'revision': rev})


class GitBlameRefreshCommand(TextCommand, GitCmd):

    HEADER_RE = re.compile(r'^(?P<sha>[0-9a-f]{40}) (\d+) (\d+) ?(\d+)?$')

    def parse_commit_line(self, commitline):
        fieldname, value = commitline.split(' ', 1)
        value = value.strip()
        if fieldname in ('committer-time', 'author-time'):
            value = int(value)
        elif fieldname in ('committer-mail', 'author-mail'):
            value = value.strip('<>')
        elif fieldname in ('previous'):
            sha, filename = value.split(' ', 1)
            value = {'commit': sha, 'file': filename}
        return fieldname, value

    def get_blame(self, filename, revision):
        data = self.git_lines(['blame', '--porcelain', revision if revision else None, '--', filename])

        commits = {}
        lines = []

        current_commit = None
        for item in data:
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

        return commits, lines

    def get_commit_date(self, commit):
        date = datetime.fromtimestamp(commit.get('committer-time'))
        return date
        # tzoffset = commit.get('committer-tz', '')
        # tzsign = tzoffset[0]
        # tzhours = int(tzoffset[1:3])
        # tzminutes = int(tzoffset[3:])

        # offset = timedelta(minutes=tzhours * 60 + tzminutes)
        # if tzsign == '-':
        #     return utcdate - offset
        # else:
        #     return utcdate + offset

    def format_blame(self, commits, lines):
        content = []
        template = "{sha} {file}({author} {date}) {line}"

        files = set(c.get('filename') for _, c in commits.items())
        max_file = max(len(f) for f in files)
        max_name = max(len(c.get('committer', '')) for _, c in commits.items())

        for sha, line in lines:
            commit = commits.get(sha)
            date = self.get_commit_date(commit)
            c = template.format(
                sha=sha[:8],
                file=commit.get('filename').ljust(max_file + 1) if len(files) > 1 else '',
                author=commit.get('committer', '').ljust(max_name + 1, ' '),
                date=date.strftime("%a %b %H:%M:%S %Y"),
                line=line
            )
            content.append(c)
        return "\n".join(content)

    def is_visible(self):
        return False

    def run(self, edit, filename=None, revision=None):
        filename = filename or self.view.settings().get('git_blame_file')
        revision = revision or self.view.settings().get('git_blame_rev')

        commits, lines = self.get_blame(filename, revision)
        blame = self.format_blame(commits, lines)

        if blame:
            self.view.set_read_only(False)
            if self.view.size() > 0:
                self.view.erase(edit, sublime.Region(0, self.view.size()))
            self.view.insert(edit, 0, blame)
            self.view.set_read_only(True)
