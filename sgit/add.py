# coding: utf-8
import sublime
from sublime_plugin import WindowCommand, TextCommand

from .cmd import GitCmd
from .status import GIT_WORKING_DIR_CLEAN

GIT_ADD_ALL = "+ All files"
GIT_ADD_ALL_UNSTAGED = "+ All unstaged files"


class GitQuickAddCommand(WindowCommand, GitCmd):
    """ Autodoc?

    Test
    """

    def run(self):
        status = self.get_status_list()

        def on_done(idx):
            if idx == -1:
                return
            line = status[idx]
            if line == GIT_WORKING_DIR_CLEAN:
                return
            elif line == GIT_ADD_ALL_UNSTAGED:
                self.git(['add', '--update', '.'])
            elif line == GIT_ADD_ALL:
                self.git(['add', '--all'])
            else:
                worktree, filename = status[idx][0], status[idx][2:]
                if worktree == '?':
                    self.git(['add', '--', filename])
                else:
                    self.git(['add', '--update', '--', filename])
            self.window.run_command('git_quick_add')

        self.window.show_quick_panel(status, on_done, sublime.MONOSPACE_FONT)

    def get_status_list(self):
        status = [l[1:] for l in self.git_lines(['status', '--porcelain', '-u']) if l[1] != ' ']
        if not status:
            return [GIT_WORKING_DIR_CLEAN]
        if len(status) > 1:
            if any([l[0] == '?' for l in status]):
                status.append(GIT_ADD_ALL)
            if any([l[0] != '?' for l in status]):
                status.append(GIT_ADD_ALL_UNSTAGED)
        return status


class GitAddCurrentFileCommand(TextCommand, GitCmd):
    """ Adds current file to git

    :shortcut OS X: ``ctrl+k``
    :shortcut Windows: ``ctrl+k``

    Hejsa mere info
    """

    def run(self, edit):
        filename = self.view.file_name()
        if not filename:
            sublime.error_message('Cannot add a file which has not been saved.')
            return

        exit, stdout = self.git(['add', '--force', '--', filename])
        if exit != 0:
            sublime.error_message('git error: %s' % stdout)
