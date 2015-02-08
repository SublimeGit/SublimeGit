# coding: utf-8
import os
import subprocess
import threading
import sublime
from sublime_plugin import WindowCommand

from .util import get_executable
from .cmd import GitCmd


EXECUTABLE_ERROR = ("Executable '{bin}' was not found in PATH. Current PATH:\n\n"
                    "{path}")


class GitGitkCommand(WindowCommand, GitCmd):
    """
    Documentation coming soon.
    """

    def run(self):
        cwd = self.get_repo(silent=False)
        if not cwd:
            return

        cmd = get_executable('gitk', ['gitk'])
        startupinfo = self.startupinfo()
        environment = self.env()

        def async_inner():
            try:
                os.chdir(cwd)
                proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            startupinfo=startupinfo,
                            env=environment)
                proc.wait()
            except OSError:
                path = "\n".join(os.environ.get('PATH', '').split(':'))
                msg = EXECUTABLE_ERROR.format(bin='gitk', path=path)
                sublime.error_message(msg)

        thread = threading.Thread(target=async_inner)
        thread.start()
