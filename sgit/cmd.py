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


logger = logging.getLogger(__name__)


GIT_INIT_DIALOG = ("Could not find any git repositories based on the open files and folders. "
                   "Do you want to initialize a repository?")


class SublimeGitException(Exception):
    pass


class Cmd(object):
    started_at = datetime.today()
    last_popup_at = None

    executable = None
    bin = []
    opts = []

    # working dir remake
    def get_dir_from_view(self, view=None):
        d = None
        if view and view.file_name():
            d = os.path.realpath(os.path.dirname(view.file_name()))
            logger.info('get_dir_from_view(view=%s): %s', view.id(), d)
        return d

    def get_dirs_from_window_folders(self, window=None):
        dirs = set()
        if window:
            dirs = set(f for f in window.folders())
            logger.info('get_dirs_from_window_folders(window=%s): %s', window.id(), dirs)
        return dirs

    def get_dirs_from_window_views(self, window=None):
        dirs = set()
        if window:
            view_dirs = [self.get_dir_from_view(v) for v in window.views()]
            dirs = set(d for d in view_dirs if d)
            logger.info('get_dirs_from_window_views(window=%s): %s', window.id(), dirs)
        return dirs

    def get_dirs(self, window=None):
        dirs = set()
        if window:
            dirs |= self.get_dirs_from_window_folders(window)
            dirs |= self.get_dirs_from_window_views(window)
            logger.info('get_dirs(window=%s): %s', window.id(), dirs)
        return dirs

    def get_dirs_prioritized(self, window=None):
        dirs = list()
        if window:
            all_dirs = self.get_dirs(window)
            active_view_dir = self.get_dir_from_view(window.active_view())
            if active_view_dir:
                dirs.append(active_view_dir)
                all_dirs.discard(active_view_dir)
            for d in sorted(list(all_dirs), key=lambda x: len(x), reverse=True):
                dirs.append(d)
            logger.info('get_dirs_prioritized(window=%s): %s', window.id(), dirs)
        return dirs

    # path walking
    def all_dirnames(self, directory):
        dirnames = [directory]
        while directory and directory != os.path.dirname(directory):
            directory = os.path.dirname(directory)
            dirnames.append(directory)
            logger.info('all_dirs(directory=%s): %s', directory, dirnames)
        return dirnames

    # git repos
    def is_git_repo(self, directory):
        git_dir = os.path.join(directory, '.git')
        return os.path.exists(git_dir)

    def find_git_repos(self, directories):
        repos = set()
        for directory in directories:
            for dirname in self.all_dirnames(directory):
                if self.is_git_repo(dirname):
                    repos.add(dirname)
        return repos

    def git_repos_from_window(self, window=None):
        repos = set()
        if window:
            dirs = self.get_dirs_prioritized(window)
            for repo in self.find_git_repos(dirs):
                repos.add(repo)
        return repos

    def git_repo_from_view(self, view=None):
        if view:
            view_dir = self.get_dir_from_view(view)
            if view_dir:
                repos = list(self.find_git_repos([view_dir]))
                for repo in sorted(list(repos), key=lambda x: len(x), reverse=True):
                    return repo
        return None

    def get_repo(self, silent=True):
        repo = None

        if hasattr(self, 'view'):
            repo = self.get_repo_from_view(self.view, silent=silent)
            if self.view.window():
                if not repo:
                    repo = self.get_repo_from_window(self.view.window(), silent=silent)
        elif hasattr(self, 'window'):
            repo = self.get_repo_from_window(self.window, silent=silent)

        return repo

    def get_repo_from_view(self, view=None, silent=True):
        if not view:
            return

        # first try the view settings (for things like status, diff, etc)
        view_repo = view.settings().get('git_repo')
        if view_repo:
            logger.info('get_repo_from_view(view=%s, silent=%s): %s (view settings)', view.id(), silent, view_repo)
            return view_repo

        # else try the given view file
        file_repo = self.git_repo_from_view(view)
        if file_repo:
            logger.info('get_repo(window=%s, silent=%s): %s (file)', view.id(), silent, file_repo)
            return file_repo

    def get_repo_from_window(self, window=None, silent=True):
        if not window:
            return

        active_view = window.active_view()
        if active_view:
            # if the active view has a setting, use that
            active_view_repo = active_view.settings().get('git_repo')
            if active_view_repo:
                logger.info('get_repo_from_window(window=%s, silent=%s): %s (view settings)', window.id(), silent, active_view_repo)
                return active_view_repo

            # if the active view has a filename, use that
            active_file_repo = self.git_repo_from_view(active_view)
            if active_file_repo:
                logger.info('get_repo_from_window(window=%s, silent=%s): %s (active file)', window.id(), silent, active_file_repo)
                return active_file_repo

        # find all possible repos
        any_repos = self.git_repos_from_window(window)

        # if there is only one repository, use that
        if len(any_repos) == 1:
            only_repo = any_repos.pop()
            logger.info('get_repo_from_window(window=%s, silent=%s): %s (only repo)', window.id(), silent, only_repo)
            return only_repo

        if silent:
            return

        if any_repos:
            window.run_command('git_switch_repo')
        else:
            if sublime.ok_cancel_dialog(GIT_INIT_DIALOG, 'Initialize repository'):
                window.run_command('git_init')

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
    def cmd(self, cmd, stdin=None, cwd=None, ignore_errors=False):
        if not cwd:
            cwd = self.get_repo(silent=False)
            if not cwd:
                raise SublimeGitException("Could not find repo.")

        command = self.build_command(cmd)
        try:
            logger.debug("cmd: %s", command)

            encoding = get_setting('encoding', 'utf-8')
            if stdin:
                stdin = stdin.encode(encoding)

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
        if not cwd:
            cwd = self.get_repo(silent=False)
            if not cwd:
                return

        command = self.build_command(cmd)
        encoding = get_setting('encoding', 'utf-8')

        def async_inner(cmd, cwd, encoding, on_data=None, on_complete=None, on_error=None, on_exception=None):
            try:
                logger.debug('async-cmd: %s', cmd)

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


class GitCmd(Cmd):
    executable = 'git'
    bin = ['git']
    opts = ['--no-pager']

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


class GitFlowCmd(Cmd):
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


class LegitCmd(Cmd):
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
