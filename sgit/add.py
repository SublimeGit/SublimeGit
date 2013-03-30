# coding: utf-8
import sublime
from sublime_plugin import WindowCommand, TextCommand

from .cmd import GitCmd
from .status import GIT_WORKING_DIR_CLEAN

GIT_ADD_ALL = "+ All files"
GIT_ADD_ALL_UNSTAGED = "+ All unstaged files"


class GitQuickAddCommand(WindowCommand, GitCmd):
    """
    Adds one or more files to the staging area by selecting them
    from the quick bar.

    A list of modified files are presented in the quickbar. Each
    file is marked with a letter, indicating it's status:

    * **M** = modified
    * **A** = added
    * **D** = deleted
    * **R** = renamed
    * **C** = copied
    * **?** = untracked

    To add a file from the list, either click the file with the
    mouse, or use arrow up/arrow down or searching until you have
    the file you are looking for, and then press ``enter``. After
    adding a file, the status list will update, allowing you to
    select another file to add. To dismiss the status list, press
    ``esc``.

    When there are no more files to add, the status list will show
    the usual git message for a clean working dir. To dismiss the
    list press ``enter`` or ``esc``.

    There are two special options at the bottom of the status list.
    To go to them quickly, press arrow up which will select the
    bottom-most option. These options are:

    **+ All unstaged files**
        This option will add all changes to files git already knows
        about (all the files not marked with **?**).
    **+ All files**
        This option will add all changes to files git already knows
        about, as well as all new files (files marked with **?**).
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
    """
    This command adds the currently open file to the git
    staging area. It the --force switch, so the file will be
    added even if it matches a repository .gitignore pattern,
    or a global .gitignore pattern.

    The file must have already been saved, otherwise it won't
    exist on the filesystem, and can't be added to git.

    If the command completes successfully, no output will be
    given.
    """

    def run(self, edit):
        filename = self.view.file_name()
        if not filename:
            sublime.error_message('Cannot add a file which has not been saved.')
            return

        exit, stdout = self.git(['add', '--force', '--', filename])
        if exit != 0:
            sublime.error_message('git error: %s' % stdout)
