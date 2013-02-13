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

    def run(self):
        repos = list(self.git_repos_from_window(self.window))
        choices = []
        for repo in repos:
            basename = os.path.basename(repo)
            repo_dir = abbreviate_dir(repo)
            choices.append([basename, repo_dir])

        def on_done(idx):
            if idx != -1:
                self.on_repo(repos[idx])

        self.window.show_quick_panel(choices, on_done)

    def on_repo(self, repo):
        self.set_window_setting(self.window, 'git_repo', repo)
