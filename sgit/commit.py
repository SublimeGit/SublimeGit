# coding: utf-8
import sublime
from sublime_plugin import WindowCommand, TextCommand, EventListener

from .util import find_view_by_settings, noop
from .cmd import GitCmd
from .helpers import GitStatusHelper
from .status import GIT_WORKING_DIR_CLEAN


GIT_COMMIT_VIEW_TITLE = "COMMIT_EDITMSG"
GIT_COMMIT_VIEW_SYNTAX = 'Packages/SublimeGit/SublimeGit Commit Message.tmLanguage'
GIT_COMMIT_VIEW_SETTINGS = {
    'rulers': [72],
    'wrap_width': 72,
    'word_wrap': False,
}

GIT_NOTHING_STAGED = 'No changes added to commit. Use s on files/sections in the status view to stage changes.'
GIT_COMMIT_TEMPLATE = """
# Please enter the commit message for your changes. Lines starting
# with '#' will be ignored, and an empty message aborts the commit.
{status}"""


class GitCommit(object):

    windows = {}


class GitCommitWindowCmd(GitCmd, GitStatusHelper):

    def get_commit_template(self, add=False):
        cmd = ['commit', '--dry-run', '--status', '-a' if add else None]
        status = self.git_string(cmd)
        msg = GIT_COMMIT_TEMPLATE.format(status=status)
        return msg

    def show_commit_panel(self, content):
        panel = self.window.get_output_panel('git-commit')
        panel.run_command('git_panel_write', {'content': content})
        self.window.run_command('show_panel', {'panel': 'output.git-commit'})


class GitCommitCommand(WindowCommand, GitCommitWindowCmd):

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

            for key, val in GIT_COMMIT_VIEW_SETTINGS.items():
                view.settings().set(key, val)

        GitCommit.windows[view.id()] = (self.window, add)
        self.window.focus_view(view)

        template = self.get_commit_template(add)
        print template
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

    def on_close(self, view):
        if view.settings().get('git_view') == 'commit' and view.id() in GitCommit.windows:
            message = view.substr(sublime.Region(0, view.size()))
            window, add = GitCommit.windows[view.id()]
            window.run_command('git_commit_perform', {'message': message, 'add': add})


class GitCommitPerformCommand(WindowCommand, GitCommitWindowCmd):

    def run(self, message, add=False):
        cmd = ['commit', '--cleanup=strip', '-a' if add else None, '-F', '-']
        stdout = self.git_string(cmd, stdin=message)
        self.show_commit_panel(stdout)
        self.window.run_command('git_status_refresh')

    def is_visible(self):
        return False


class GitQuickCommitCommand(WindowCommand, GitCommitWindowCmd):

    def run(self):
        staged = self.has_staged_changes()
        dirty = self.has_unstaged_changes()

        if not staged and not dirty:
            sublime.error_message(GIT_WORKING_DIR_CLEAN.capitalize())
            return

        def on_done(msg=None):
            if not msg:
                msg = ''
            cmd = ['commit', '-F', '-'] if staged else ['commit', '-a', '-F', '-']
            stdout = self.git_string(cmd, stdin=msg)
            self.show_commit_panel(stdout)
            self.window.run_command('git_status_refresh', {'focus': False})

        self.window.show_input_panel("Commit message:", '', on_done, noop, on_done)
