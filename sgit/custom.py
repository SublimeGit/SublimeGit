# coding: utf-8
import sublime
from sublime_plugin import WindowCommand, TextCommand

import shlex

from .util import noop, StatusSpinner
from .cmd import GitCmd
from .helpers import GitErrorHelper


GIT_CUSTOM_TITLE = "*git-custom*: git "


class GitCustomCommand(WindowCommand, GitCmd, GitErrorHelper):
    """
    Execute a custom git command.

    By default, this command will be run synchronously, and the output will be presented
    in a new view, with a title corresponding to the command.

    However, it's also possible to use this command to build your own SublimeGit commands.

    It takes 3 arguments:

    * **cmd**: The command to execute (without the initial "git")
    * **async**: ``true`` to run asynchronously, ``false`` otherwise. Default: ``false``
    * **output**: ``"view"`` for a new buffer, ``"panel"`` for an output panel, ``null`` for no output. Default: ``"view"``
    * **syntax**: If output is set to ``"view"``, the new buffer will get this syntax file. Should be a name along the
                  lines of ``Packages/Python/Python.tmLanguage``. To see the current syntax for a view, execute
                  ``view.settings().get('syntax')`` from the console.

    .. note::
        See :ref:`customizations-commands` for more information on how to create your own SublimeGit commands.

    """

    def run(self, cmd=None, async=False, output="view", syntax=None):
        repo = self.get_repo()
        if not repo:
            return

        if output not in (None, "panel", "view"):
            sublime.error_message("Output parameter must be one of None, 'panel' or 'view'")
            return
        self.output = output
        self.syntax = syntax

        if not cmd:
            def on_done(cmd):
                cmd = cmd.strip()
                if not cmd:
                    return
                self.on_command(repo, cmd, async=async)

            self.window.show_input_panel('git', '', on_done, noop, noop)
        else:
            self.on_command(repo, cmd, async=async)

    def on_command(self, repo, cmd, async):
        if sublime.version() < '3000':
            cmd = cmd.encode('utf-8')
        cmd = shlex.split(cmd)
        self.init_output(repo, cmd)
        if async:
            self.run_async(repo, cmd)
        else:
            self.run_sync(repo, cmd)

    def run_sync(self, repo, cmd):
        exit, stdout, stderr = self.git(cmd, cwd=repo)
        if exit == 0:
            self.on_output(stdout)
        else:
            sublime.error_message(self.format_error_message(stderr))
        self.window.run_command('git_status', {'refresh_only': True})

    def run_async(self, repo, cmd):
        thread = self.git_async(cmd, cwd=repo, on_data=self.on_output)
        runner = StatusSpinner(thread, "Running %s" % " ".join(cmd))
        runner.start()

    def init_output(self, repo, cmd):
        if self.output == "panel":
            self.output_panel_shown = False
            self.output_panel = self.window.get_output_panel('git-custom')
        elif self.output == "view":
            self.output_view = self.window.new_file()
            self.output_view.set_name(GIT_CUSTOM_TITLE + " ".join(cmd))
            self.output_view.set_scratch(True)
            self.output_view.set_read_only(True)
            if self.syntax:
                self.output_view.set_syntax_file(self.syntax)

            self.output_view.settings().set('git_view', 'custom')
            self.output_view.settings().set('git_repo', repo)

            self.window.focus_view(self.output_view)

    def on_output(self, d):
        if self.output == "panel":
            if not self.output_panel_shown:
                self.window.run_command('show_panel', {'panel': 'output.git-custom'})
            self.output_panel.run_command('git_panel_append', {'content': d, 'scroll': True})
        elif self.output == "view":
            self.output_view.run_command('git_custom_output', {'content': d})


class GitCustomOutputCommand(TextCommand):
    _lpop = False

    def is_visible(self):
        return False

    def run(self, edit, content):
        if not self.view.settings().get('git_view') == 'custom':
            return

        self.view.set_read_only(False)
        self.view.insert(edit, self.view.size(), content)
        self.view.set_read_only(True)
