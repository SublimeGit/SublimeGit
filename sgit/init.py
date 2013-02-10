# coding: utf-8
import os

import sublime
from sublime_plugin import WindowCommand

from .util import noop, write_view, find_repo_dir
from .cmd import GitCmd


GIT_INIT_CONFIRM_MSG = """A git repository already exists in %s.
Are you sure you want to initialize a repository?"""
GIT_INIT_NO_DIR_ERROR = "No directory provided. Aborting git init."
GIT_INIT_DIR_NOT_EXISTS_MSG = "The directory %s does not exist. Create directory?"
GIT_INIT_NOT_ISDIR_ERROR = "%s is not a directory. Aborting git init."
GIT_INIT_DIR_EXISTS_ERROR = "%s already exists. Aborting git init."
GIT_INIT_DIR_LABEL = "Directory:"


class GitInitCommand(WindowCommand, GitCmd):

    def run(self):
        repo_dir = find_repo_dir(self.get_cwd())
        if repo_dir:
            init_anyway = sublime.ok_cancel_dialog(GIT_INIT_CONFIRM_MSG % repo_dir, 'Init anyway')
            if not init_anyway:
                return

        working_dir = self.get_cwd()
        initial_text = working_dir if working_dir else ''

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
        write_view(panel, output)
        self.window.run_command('show_panel', {'panel': 'output.git-init'})
