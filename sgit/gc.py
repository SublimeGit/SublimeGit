# coding: utf-8
from sublime_plugin import WindowCommand

from .util import StatusSpinner
from .cmd import GitCmd


class GitGarbageCollectCommand(WindowCommand, GitCmd):
    """
    Garbage collect

    Runs a garbage collect to pack and clean up the current
    repository.
    """

    def run(self, aggressive=None):
        repo = self.get_repo()
        if not repo:
            return

        self.panel = self.window.get_output_panel('git-gc')
        self.panel_shown = False

        thread = self.git_async(['gc', '--aggressive' if aggressive else None], cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Garbage collecting")
        runner.start()

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-gc'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})
