# coding: utf-8
from functools import partial

import sublime
from sublime_plugin import WindowCommand, TextCommand, EventListener

from .util import find_view_by_settings, noop, get_setting
from .cmd import GitCmd
from .helpers import GitStatusHelper
from .status import GIT_WORKING_DIR_CLEAN


GIT_COMMIT_VIEW_TITLE = "COMMIT_EDITMSG"
GIT_COMMIT_VIEW_SYNTAX = 'Packages/SublimeGit/syntax/SublimeGit Commit Message.tmLanguage'

GIT_NOTHING_STAGED = u'No changes added to commit. Use s on files/sections in the status view to stage changes.'
GIT_COMMIT_TEMPLATE = u"""{old_msg}
# Please enter the commit message for your changes. Lines starting
# with '#' will be ignored, and an empty message aborts the commit.
{status}"""

GIT_AMEND_PUSHED = (u"It is discouraged to rewrite history which has already been pushed. "
                    u"Are you sure you want to amend the commit?")

CUT_LINE = u"------------------------ >8 ------------------------\n"
CUT_EXPLANATION = u"# Do not touch the line above.\n# Everything below will be removed.\n"


class GitCommit(object):

    windows = {}


class GitCommitWindowCmd(GitCmd, GitStatusHelper):

    @property
    def is_verbose(self):
        return get_setting('git_commit_verbose', False)

    def get_commit_template(self, repo, add=False, amend=False):
        cmd = ['commit', '--dry-run', '--status',
               '--all' if add else None,
               '--amend' if amend else None,
               '--verbose' if self.is_verbose else None]
        exit, stdout, stderr = self.git(cmd, cwd=repo)

        stderr = stderr.strip()
        if stderr:
            for line in stderr.splitlines():
                stdout += "# %s\n" % line

        old_msg = ''
        if amend:
            old_msg = self.git_lines(['rev-list', '--format=%B', '--max-count=1', 'HEAD'], cwd=repo)
            old_msg = "%s\n" % "\n".join(old_msg[1:])

        if self.is_verbose and CUT_LINE not in stdout:
            comments = []
            other = []
            for line in stdout.splitlines():
                if line.startswith('#'):
                    comments.append(line)
                else:
                    other.append(line)
            status = "\n".join(comments)
            status += "\n# %s" % CUT_LINE
            status += CUT_EXPLANATION
            status += "\n".join(other)
        else:
            status = stdout

        return GIT_COMMIT_TEMPLATE.format(status=status, old_msg=old_msg)

    def show_commit_panel(self, content):
        panel = self.window.get_output_panel('git-commit')
        panel.run_command('git_panel_write', {'content': content})
        self.window.run_command('show_panel', {'panel': 'output.git-commit'})


class GitCommitCommand(WindowCommand, GitCommitWindowCmd):
    """
    Documentation coming soon.
    """

    def run(self, add=False):
        repo = self.get_repo()
        if not repo:
            return

        staged = self.has_staged_changes(repo)
        dirty = self.has_unstaged_changes(repo)

        if not add and not staged:
            return sublime.error_message(GIT_NOTHING_STAGED)
        elif add and (not staged and not dirty):
            return sublime.error_message(GIT_WORKING_DIR_CLEAN)

        view = find_view_by_settings(self.window, git_view='commit', git_repo=repo)
        if not view:
            view = self.window.new_file()
            view.set_name(GIT_COMMIT_VIEW_TITLE)
            view.set_syntax_file(GIT_COMMIT_VIEW_SYNTAX)
            view.set_scratch(True)

            view.settings().set('git_view', 'commit')
            view.settings().set('git_repo', repo)

        GitCommit.windows[view.id()] = (self.window, add, False)
        self.window.focus_view(view)

        template = self.get_commit_template(repo, add=add)
        view.run_command('git_commit_template', {'template': template})


class GitCommitAmendCommand(GitCommitWindowCmd, WindowCommand):
    """
    Documentation coming soon.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        unpushed = self.git_exit_code(['diff', '--exit-code', '--quiet', '@{upstream}..'], cwd=repo)
        if unpushed == 0:
            if not sublime.ok_cancel_dialog(GIT_AMEND_PUSHED, 'Amend commit'):
                return

        view = find_view_by_settings(self.window, git_view='commit', git_repo=repo)
        if not view:
            view = self.window.new_file()
            view.set_name(GIT_COMMIT_VIEW_TITLE)
            view.set_syntax_file(GIT_COMMIT_VIEW_SYNTAX)
            view.set_scratch(True)

            view.settings().set('git_view', 'commit')
            view.settings().set('git_repo', repo)

        GitCommit.windows[view.id()] = (self.window, False, True)
        self.window.focus_view(view)

        template = self.get_commit_template(repo, amend=True)
        view.run_command('git_commit_template', {'template': template})


class GitCommitTemplateCommand(TextCommand):

    def is_visible(self):
        return False

    def run(self, edit, template=''):
        if self.view.size() > 0:
            self.view.erase(edit, sublime.Region(0, self.view.size()))
        self.view.insert(edit, 0, template)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0))


class GitCommitEventListener(EventListener):
    _lpop = False

    def mark_pedantic(self, view):
        if view.settings().get('git_view') == 'commit' or view.file_name() == 'COMMIT_EDITMSG':
            # Header lines should be a max of 50 chars
            view.erase_regions('git-commit.header')
            firstline = view.line(view.text_point(0, 0))
            if firstline.end() > 50 and not view.substr(firstline).startswith('#'):
                view.add_regions('git-commit.header', [sublime.Region(50, firstline.end())], 'invalid', 'dot')

            # The second line should be empty
            view.erase_regions('git-commit.line2')
            secondline = view.line(view.text_point(1, 0))
            if secondline.end() - secondline.begin() > 0 and not view.substr(secondline).startswith('#'):
                view.add_regions('git-commit.line2', [secondline], 'invalid', 'dot')

            # Other lines should be at most 72 chars
            view.erase_regions('git-commit.others')
            for l in view.lines(sublime.Region(view.text_point(2, 0), view.size())):
                if view.substr(l).startswith('#'):
                    break
                if l.end() - l.begin() > 72:
                    view.add_regions('git-commit.others', [sublime.Region(l.begin() + 72, l.end())], 'invalid', 'dot')

    def on_activated(self, view):
        if sublime.version() < '3000' and get_setting('git_commit_pedantic') is True:
            self.mark_pedantic(view)

    def on_modified(self, view):
        if sublime.version() < '3000' and get_setting('git_commit_pedantic') is True:
            self.mark_pedantic(view)

    def on_modified_async(self, view):
        if get_setting('git_commit_pedantic') is True:
            self.mark_pedantic(view)

    def on_activated_async(self, view):
        if get_setting('git_commit_pedantic') is True:
            self.mark_pedantic(view)

    def on_close(self, view):
        if view.settings().get('git_view') == 'commit' and view.id() in GitCommit.windows:
            message = view.substr(sublime.Region(0, view.size()))
            window, add, amend = GitCommit.windows[view.id()]
            repo = view.settings().get('git_repo')
            window.run_command('git_commit_perform', {'message': message, 'add': add, 'amend': amend, 'repo': repo})


class GitCommitPerformCommand(WindowCommand, GitCommitWindowCmd):

    def run(self, repo, message, add=False, amend=False):
        cmd = ['commit', '--cleanup=strip',
               '--all' if add else None,
               '--amend' if amend else None,
               '--verbose' if self.is_verbose else None, '-F', '-']

        exit, stdout, stderr = self.git(cmd, stdin=message, cwd=repo)

        self.show_commit_panel(stdout if exit == 0 else stderr)
        self.window.run_command('git_status', {'refresh_only': True})

    def is_visible(self):
        return False


class GitCommitSaveCommand(TextCommand):

    def is_visible(self):
        return False

    def run(self, edit):
        if self.view.settings().get('git_view') == 'commit' and self.view.id() in GitCommit.windows:
            return
        self.view.run_command('save')


class GitQuickCommitCommand(WindowCommand, GitCommitWindowCmd):
    """
    Quickly commit changes with a one-line commit message.

    If there are any staged changes, only those changes will be added. If there
    are no staged changes, any changed files that git know about will be added
    in the commit.

    If the working directory is clean, an error will be shown indicating it.

    After entering the commit message, press enter to commit, or esc to cancel.
    An empty commit message will also result in the commit being cancelled.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        staged = self.has_staged_changes(repo)
        dirty = self.has_unstaged_changes(repo)

        if not staged and not dirty:
            sublime.error_message(GIT_WORKING_DIR_CLEAN.capitalize())
            return

        self.window.show_input_panel("Commit message:", '', partial(self.on_commit_message, repo), noop, noop)

    def on_commit_message(self, repo, msg=None):
        if not msg:
            msg = ''
        cmd = ['commit', '-F', '-'] if self.has_staged_changes(repo) else ['commit', '-a', '-F', '-']
        stdout = self.git_string(cmd, stdin=msg, cwd=repo)
        self.show_commit_panel(stdout)
        self.window.run_command('git_status', {'refresh_only': True})


class GitQuickCommitCurrentFileCommand(TextCommand, GitCmd, GitStatusHelper):
    """
    Documentation coming soon.
    """

    def run(self, edit):
        filename = self.view.file_name()
        if not filename:
            sublime.error_message("Cannot commit a file which has not been saved.")
            return

        repo = self.get_repo()
        if not repo:
            return

        if not self.file_in_git(repo, filename):
            if sublime.ok_cancel_dialog("The file %s is not tracked by git. Do you want to add it?" % filename, "Add file"):
                exit, stdout, stderr = self.git(['add', '--force', '--', filename], cwd=repo)
                if exit == 0:
                    sublime.status_message('Added %s' % filename)
                else:
                    sublime.error_message('git error: %s' % stderr)
            else:
                return

        self.view.window().show_input_panel("Commit message:", '', partial(self.on_commit_message, repo, filename), noop, noop)

    def on_commit_message(self, repo, filename, msg=None):
        if not msg:
            msg = ''

        # run command
        cmd = ['commit', '-F', '-', '--only', '--', filename]
        stdout = self.git_string(cmd, stdin=msg, cwd=repo)

        # show output panel
        panel = self.view.window().get_output_panel('git-commit')
        panel.run_command('git_panel_write', {'content': stdout})
        self.view.window().run_command('show_panel', {'panel': 'output.git-commit'})

        # update status if necessary
        self.view.window().run_command('git_status', {'refresh_only': True})
