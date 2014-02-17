# coding: utf-8
import os
import sys
import subprocess
import logging
import threading
import webbrowser
from datetime import datetime
from functools import partial

import sublime

from .util import get_executable, get_setting
from .helpers import GitRepoHelper


logger = logging.getLogger('SublimeGit.cmd')


class SublimeGitException(Exception):
    pass


class Cmd(object):
    started_at = datetime.today()
    last_popup_at = None

    executable = None
    bin = []
    opts = []

    # license stuff
    def __get_license(self):
        email = get_setting('email')
        key = get_setting('product_key')
        if email is None or len(email) == 0:
            return None
        if key is None or len(key) != 32:
            return None
        return (email, key)

    def __validate_license(self, license):
        data, key = license
        i = 0
        s1, s2 = 0, 0
        try:
            c = ((int(key[-2:], 16) + 8) ^ 0xff) * 8
        except ValueError:
            return False
        while i <= 1848:
            s1 = (s1 + (ord(data[i]) & 0xff)) % 0xffff
            s2 = (s1 + s2) % 0xffff
            data += "%x" % ((s2 << 16) | s1)
            i += 1
            if i == c and data[-30:] == key[:-2]:
                return True
        return False

    URL = 'https://sublimegit.net/buy?utm_source=st%s&utm_medium=popup&utm_campaign=buy'
    LICENSE_POPUP = "SublimeGit Evaluation\n\nI hope you are enjoying SublimeGit. " +\
                    "If you are, please consider buying a license at https://sublimegit.net"

    def __license_popup(self):
        url = self.URL % sys.version_info[0]
        if sublime.ok_cancel_dialog(self.LICENSE_POPUP, 'Buy SublimeGit'):
            webbrowser.open(url)

    def __check_license(self):
        seconds_since_start = (datetime.today() - Cmd.started_at).seconds
        seconds_since_popup = (datetime.today() - Cmd.last_popup_at).seconds if Cmd.last_popup_at else None

        if hasattr(self, '_lpop') and self._lpop is False:
            return
        if seconds_since_start < 30 * 60:
            return
        if seconds_since_popup is not None and seconds_since_popup < 120 * 60:
            return

        license = self.__get_license()
        if not license or not self.__validate_license(license):
            sublime.set_timeout(self.__license_popup, 0)
            Cmd.last_popup_at = datetime.today()

    # cmd helpers
    def _string(self, cmd, strip=True, *args, **kwargs):
        _, stdout, _ = self.cmd(cmd, *args, **kwargs)
        return stdout.strip() if strip else stdout

    def _lines(self, cmd, *args, **kwargs):
        _, stdout, _ = self.cmd(cmd, *args, **kwargs)
        stdout = stdout.rstrip()
        if not stdout:
            return []
        return stdout.split('\n')

    def _exit_code(self, cmd, *args, **kwargs):
        exit, _, _ = self.cmd(cmd, *args, **kwargs)
        return exit

    def build_command(self, cmd):
        bin = get_executable(self.executable, self.bin)
        return bin + self.opts + [c for c in cmd if c]

    def startupinfo(self):
        startupinfo = None
        if hasattr(subprocess, 'STARTUPINFO'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo

    # sync commands
    def cmd(self, cmd, stdin=None, cwd=None, ignore_errors=False, encoding=None):
        encoding = encoding or get_setting('encoding', 'utf-8')

        command = self.build_command(cmd)
        try:
            logger.debug("cmd: %s", command)

            if stdin:
                stdin = stdin.encode(encoding)

            if cwd:
                os.chdir(cwd)

            proc = subprocess.Popen(command,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    startupinfo=self.startupinfo())
            stdout, stderr = proc.communicate(stdin)

            logger.debug("out: (%s) %s", proc.returncode, [stdout[:100]])

            self.__check_license()

            return (proc.returncode, stdout.decode(encoding), stderr.decode(encoding))
        except OSError as e:
            if ignore_errors:
                return (0, '')
            sublime.error_message(self.get_executable_error())
            raise SublimeGitException("Could not execute command: %s" % e)

    # async commands
    def cmd_async(self, cmd, cwd=None, **callbacks):
        command = self.build_command(cmd)
        encoding = get_setting('encoding', 'utf-8')

        def async_inner(cmd, cwd, encoding, on_data=None, on_complete=None, on_error=None, on_exception=None):
            try:
                logger.debug('async-cmd: %s', cmd)

                if cwd:
                    os.chdir(cwd)

                proc = subprocess.Popen(cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        startupinfo=self.startupinfo())

                for line in iter(proc.stdout.readline, b''):
                    logger.debug('async-out: %s', line.strip())
                    line = line.decode(encoding)
                    if callable(on_data):
                        sublime.set_timeout(partial(on_data, line), 0)

                proc.wait()
                logger.debug('async-exit: %s', proc.returncode)
                if proc.returncode == 0:
                    if callable(on_complete):
                        sublime.set_timeout(partial(on_complete, proc.returncode), 0)
                else:
                    if callable(on_error):
                        sublime.set_timeout(partial(on_error, proc.returncode), 0)

            except OSError as e:
                logger.debug('async-exception: %s' % e)
                if callable(on_exception):
                    sublime.set_timeout(partial(on_exception, e), 0)

        thread = threading.Thread(target=partial(async_inner, command, cwd, encoding, **callbacks))
        return thread

    # messages
    EXECUTABLE_ERROR = ("Executable '{bin}' was not found in PATH. Current PATH:\n\n"
                        "{path}\n\n"
                        "Try adjusting the git_executables['{executable}'] setting.")

    def get_executable_error(self):
        path = "\n".join(os.environ.get('PATH', '').split(':'))
        return self.EXECUTABLE_ERROR.format(executable=self.executable,
                                            path=path,
                                            bin=self.bin)


class GitCmd(GitRepoHelper, Cmd):
    executable = 'git'
    bin = ['git']
    opts = [
        '--no-pager',
        '-c', 'color.diff=false',
        '-c', 'color.status=false',
        '-c', 'color.branch=false',
        '-c', 'status.displayCommentPrefix=true',
        '-c', 'core.commentchar=#',
    ]

    def git(self, cmd, *args, **kwargs):
        return self.cmd(cmd, *args, **kwargs)

    def git_string(self, cmd, *args, **kwargs):
        return self._string(cmd, *args, **kwargs)

    def git_lines(self, cmd, *args, **kwargs):
        return self._lines(cmd, *args, **kwargs)

    def git_exit_code(self, cmd, *args, **kwargs):
        return self._exit_code(cmd, *args, **kwargs)

    def git_async(self, cmd, *args, **kwargs):
        return self.cmd_async(cmd, *args, **kwargs)


class GitFlowCmd(GitRepoHelper, Cmd):
    executable = 'git_flow'
    bin = ['git-flow']

    def git_flow(self, cmd, *args, **kwargs):
        return self.cmd(cmd, *args, **kwargs)

    def git_flow_string(self, cmd, *args, **kwargs):
        return self._string(cmd, *args, **kwargs)

    def git_flow_lines(self, cmd, *args, **kwargs):
        return self._lines(cmd, *args, **kwargs)

    def git_flow_exit_code(self, cmd, *args, **kwargs):
        return self._exit_code(cmd, *args, **kwargs)

    def git_flow_async(self, cmd, *args, **kwargs):
        return self.cmd_async(cmd, *args, **kwargs)


class LegitCmd(GitRepoHelper, Cmd):
    executable = 'legit'
    bin = ['legit']

    def legit(self, cmd, *args, **kwargs):
        return self.cmd(cmd, *args, **kwargs)

    def legit_string(self, cmd, *args, **kwargs):
        return self._string(cmd, *args, **kwargs)

    def legit_lines(self, cmd, *args, **kwargs):
        return self._lines(cmd, *args, **kwargs)

    def legit_exit_code(self, cmd, *args, **kwargs):
        return self._exit_code(cmd, *args, **kwargs)

    def legit_async(self, cmd, *args, **kwargs):
        return self.cmd_async(cmd, *args, **kwargs)
