# coding: utf-8
from functools import partial
import sublime
from sublime_plugin import WindowCommand, TextCommand, EventListener

from .util import find_view_by_settings, noop, get_setting
from .cmd import GitCmd
from .helpers import GitStatusHelper
from .status import GIT_WORKING_DIR_CLEAN


GIT_COMMIT_VIEW_TITLE = "COMMIT_EDITMSG"
GIT_COMMIT_VIEW_SYNTAX = 'Packages/SublimeGit/SublimeGit Commit Message.tmLanguage'

GIT_NOTHING_STAGED = u'No changes added to commit. Use s on files/sections in the status view to stage changes.'
GIT_COMMIT_TEMPLATE = u"""
# Please enter the commit message for your changes. Lines starting
# with '#' will be ignored, and an empty message aborts the commit.
{status}"""


class GitCommit(object):

    windows = {}


class GitCommitWindowCmd(GitCmd, GitStatusHelper):

    @property
    def is_verbose(self):
        return get_setting('git_commit_verbose', True)

    def get_commit_template(self, add=False):
        cmd = ['-c', 'color.diff=false', '-c', 'color.status=false', 'commit', '--dry-run', '--status',
               '--all' if add else None,
               '--verbose' if self.is_verbose else None]
        status = self.git_string(cmd)
        msg = GIT_COMMIT_TEMPLATE.format(status=status)
        return msg

    def show_commit_panel(self, content):
        panel = self.window.get_output_panel('git-commit')
        panel.run_command('git_panel_write', {'content': content})
        self.window.run_command('show_panel', {'panel': 'output.git-commit'})


class GitCommitCommand(WindowCommand, GitCommitWindowCmd):
    """
    Documentation coming soon.
    """

    def run(self, add=False):
        repo = self.get_repo(self.window)
        if not repo:
            return

        staged = self.has_staged_changes()
        dirty = self.has_unstaged_changes()

        if not add and not staged:
            sublime.error_message(GIT_NOTHING_STAGED)
            return
        elif add and (not staged and not dirty):
            sublime.error_message(GIT_WORKING_DIR_CLEAN)
            return

        view = find_view_by_settings(self.window, git_view='commit', git_repo='repo')
        if not view:
            view = self.window.new_file()
            view.set_name(GIT_COMMIT_VIEW_TITLE)
            view.set_syntax_file(GIT_COMMIT_VIEW_SYNTAX)
            view.set_scratch(True)

            view.settings().set('git_view', 'commit')
            view.settings().set('git_repo', repo)

        GitCommit.windows[view.id()] = (self.window, add)
        self.window.focus_view(view)

        template = self.get_commit_template(add)
        view.run_command('git_commit_template', {'template': template})


class GitCommitTemplateCommand(TextCommand):

    def is_visible(self):
        return True

    def run(self, edit, template=''):
        if self.view.size() > 0:
            self.view.erase(edit, sublime.Region(0, self.view.size()))
        self.view.insert(edit, 0, template)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(0))


class GitCommitEventListener(EventListener):
    _lpop = False

    def on_close(self, view):
        if view.settings().get('git_view') == 'commit' and view.id() in GitCommit.windows:
            message = view.substr(sublime.Region(0, view.size()))
            window, add = GitCommit.windows[view.id()]
            window.run_command('git_commit_perform', {'message': message, 'add': add})


class GitCommitPerformCommand(WindowCommand, GitCommitWindowCmd):

    def run(self, message, add=False):
        cmd = ['commit', '--cleanup=strip', '-a' if add else None, '--verbose' if self.is_verbose else None, '-F', '-']
        stdout = self.git_string(cmd, stdin=message)
        self.show_commit_panel(stdout)
        self.window.run_command('git_status', {'refresh_only': True})

    def is_visible(self):
        return False


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
        staged = self.has_staged_changes()
        dirty = self.has_unstaged_changes()

        if not staged and not dirty:
            sublime.error_message(GIT_WORKING_DIR_CLEAN.capitalize())
            return

        self.window.show_input_panel("Commit message:", '', self.on_commit_message, noop, noop)

    def on_commit_message(self, msg=None):
        if not msg:
            msg = ''
        cmd = ['commit', '-F', '-'] if self.has_staged_changes() else ['commit', '-a', '-F', '-']
        stdout = self.git_string(cmd, stdin=msg)
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

        if not self.file_in_git(filename):
            if sublime.ok_cancel_dialog("The file %s is not tracked by git. Do you want to add it?" % filename, "Add file"):
                exit, stdout = self.git(['add', '--force', '--', filename])
                if exit == 0:
                    sublime.status_message('Added %s' % filename)
                else:
                    sublime.error_message('git error: %s' % stdout)
            else:
                return

        self.view.window().show_input_panel("Commit message:", '', partial(self.on_commit_message, filename), noop, noop)

    def on_commit_message(self, filename, msg=None):
        if not msg:
            msg = ''

        # run command
        cmd = ['commit', '-F', '-', '--only', '--', filename]
        stdout = self.git_string(cmd, stdin=msg)

        # show output panel
        panel = self.view.window().get_output_panel('git-commit')
        panel.run_command('git_panel_write', {'content': stdout})
        self.view.window().run_command('show_panel', {'panel': 'output.git-commit'})

        # update status if necessary
        self.view.window().run_command('git_status', {'refresh_only': True})
