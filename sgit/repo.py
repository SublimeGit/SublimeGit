# coding: utf-8
import os

import sublime
from sublime_plugin import WindowCommand

from .util import noop, abbreviate_dir
from .cmd import GitCmd


GIT_INIT_NO_DIR_ERROR = "No directory provided. Aborting git init."
GIT_INIT_DIR_NOT_EXISTS_MSG = "The directory %s does not exist. Create directory?"
GIT_INIT_NOT_ISDIR_ERROR = "%s is not a directory. Aborting git init."
GIT_INIT_DIR_EXISTS_ERROR = "%s already exists. Aborting git init."
GIT_INIT_DIR_LABEL = "Directory:"


class GitInitCommand(WindowCommand, GitCmd):
    """
    Initializes a git repository in a specified directory.

    An input panel will be shown in the bottom of the Sublime Text
    window, allowing you to edit the directory which will be initialized
    as a git repository. After choosing the directory, press ``enter``
    to complete. To abort, press ``esc``.

    If the directory does not already exist, you will be asked if you
    want to create it. If the path already exists, but it is not a
    directory, or if it is a directory and already contains git repository,
    the command will exit with an error message.

    .. note::
        The initial suggestion for the directory is calculated in the
        following way:

        1. The first open folder, if any.
        2. The directory name of the currently active file, if any.
        3. The directory name of the first open file which has a filename,
           if any.
        4. The user directory of the currently logged in user.
    """

    def get_dir_candidate(self):
        if self.window:
            if self.window.folders():
                return self.window.folders()[0]

            active_dir = self.get_dir_from_view(self.window.active_view())
            if active_dir:
                return active_dir

            for view in self.window.views():
                view_dir = self.get_dir_from_view(view)
                if view_dir:
                    return view_dir
        return os.path.expanduser('~')

    def run(self):
        dir_candidate = self.get_dir_candidate()
        initial_text = dir_candidate if dir_candidate else ''
        self.window.show_input_panel(GIT_INIT_DIR_LABEL, initial_text, self.on_done, noop, noop)

    def on_done(self, directory):
        directory = directory.strip()
        if not directory:
            sublime.error_message(GIT_INIT_NO_DIR_ERROR)
            return

        if not os.path.exists(directory):
            create = sublime.ok_cancel_dialog(GIT_INIT_DIR_NOT_EXISTS_MSG % directory, 'Create')
            if create:
                os.makedirs(directory)
            else:
                return

        directory = os.path.realpath(directory)
        if not os.path.isdir(directory):
            sublime.error_message(GIT_INIT_NOT_ISDIR_ERROR % directory)
            return

        git_dir = os.path.join(directory, '.git')
        if os.path.exists(git_dir):
            sublime.error_message(GIT_INIT_DIR_EXISTS_ERROR % git_dir)
            return

        output = self.git_string(['init'], cwd=directory)
        panel = self.window.get_output_panel('git-init')
        panel.run_command('git_panel_write', {'content': output})
        self.window.run_command('show_panel', {'panel': 'output.git-init'})


class GitSwitchRepoCommand(WindowCommand, GitCmd):
    """
    Switch the active repository for the current Sublime Text window.

    In SublimeGit, each window has an active repository. The first time
    you execute a git command, SublimeGit will try to find out which
    repository should be the active one for the current window. If there
    are multiple possible repositories, you will be presented with a list
    to choose from. Your selection will then be set as the active repository
    for the window.

    If you generally only have one folder open per window in Sublime
    Text and don't use git submodules, then you probably won't have
    to switch repositories manually. However, there are some situations
    where it can be necessary to do so:

    **Nested git repositories**
        If you are using git submodules, or some kind of package manager
        which uses git checkouts in a subfolder of your project to hold
        packages (such as Composer for PHP), and you want to explicitly
        specify that you are working inside the nested repository.
    **Multiple folders or files**
        If you have multiple folders or multiple files, which are managed
        with git, open in the same Sublime Text window, and you want to
        switch the repository that you are currently working on.

    .. note::

        **How does SublimeGit find my repositories?**

        Excellent question. SublimeGit will try it's best to guess which
        repository you are working on. In general it works something like
        this:

        * Find the currently active file.

          * Is it a git view? Use that repository.
          * Is any of the parents a git repository? Use that.

        * If that fails, find the currently active window.

          * Find a list of all possible directories:

            * The directories of any open folders.
            * The directories of any open files.

          * Generate a list of all of the parents of these directories.
          * Check to see if any of the directories or their parents are
            git repositories.

        * Select a repository:

          * If there is only one repository then use that.
          * If there are more than one repository, present a list to
            choose from.
    """

    def run(self):
        repos = list(self.git_repos_from_window(self.window))
        choices = []
        for repo in repos:
            basename = os.path.basename(repo)
            repo_dir = abbreviate_dir(repo)
            choices.append([basename, repo_dir])

        def on_done(idx):
            if idx != -1:
                self.set_window_repository(self.window, repo)

        self.window.show_quick_panel(choices, on_done)
