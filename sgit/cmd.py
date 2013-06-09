# coding: utf-8
import os
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


class CmdBase(type):

    def __new__(cls, name, bases, attrs):
        # get executable from attributes and remove it
        executable = attrs.pop('__executable__', None)
        default_bin = attrs.pop('__bin__', [])
        opts = attrs.pop('__opts__', [])

        # create a class to work with
        new_class = super(CmdBase, cls).__new__(cls, name, bases, attrs)

        # just return the sucker if it does not have an executable. Nothing to see here!
        if not executable:
            return new_class

        # Get the executable from the settings
        bin = get_executable(executable, default_bin)

        setattr(new_class, 'executable', executable)
        setattr(new_class, 'bin', bin)

        # Make sure that it exists
        # which -s ex return code

        # add default options to bin

        def CMD(self, cmd, *args, **kwargs):
            return self.cmd(bin + opts + cmd, *args, **kwargs)

        def CMD_string(self, cmd, *args, **kwargs):
            return self._string(self.cmd(bin + opts + cmd, *args, **kwargs))

        def CMD_lines(self, cmd, *args, **kwargs):
            return self._lines(self.cmd(bin + opts + cmd, *args, **kwargs))

        def CMD_exit_code(self, cmd, *args, **kwargs):
            return self._exit_code(self.cmd(bin + opts + cmd, *args, **kwargs))

        def CMD_async(self, cmd, *args, **kwargs):
            return self.cmd_async(bin + opts + cmd, *args, **kwargs)

        for f in (CMD, CMD_string, CMD_lines, CMD_exit_code, CMD_async):
            setattr(new_class, f.__name__.replace('CMD', executable), f)

        return new_class


class Cmd(object):
    __metaclass__ = CmdBase
    started_at = datetime.today()
    last_popup_at = None

    # helper for getting window in text- and windowcommands
    def get_window(self):
        return self.view.window() if hasattr(self, 'view') else self.window

    # per-window state
    @property
    def window_settings(self):
        if not hasattr(self, '_settings'):
            self._settings = sublime.load_settings('SublimeGitWindowSettings')
        return self._settings

    def get_window_setting(self, window, key, default=None):
        return self.window_settings.get(key, {}).get(str(window.id()), default)

    def set_window_setting(self, window, key, value):
        vals = self.window_settings.get(key, {})
        vals[str(window.id())] = value
        self.window_settings.set(key, vals)

    # working dir remake
    def get_dir_from_view(self, view=None):
        if view and view.file_name():
            return os.path.realpath(os.path.dirname(view.file_name()))

    def get_dirs_from_window_folders(self, window=None):
        if window:
            return set(f for f in window.folders())
        return set()

    def get_dirs_from_window_views(self, window=None):
        if window:
            view_dirs = [self.get_dir_from_view(v) for v in window.views()]
            return set(d for d in view_dirs if d)
        return set()

    def get_dirs(self, window=None):
        dirs = set()
        if window:
            dirs |= self.get_dirs_from_window_folders(window)
            dirs |= self.get_dirs_from_window_views(window)
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
        return dirs

    # path walking
    def all_dirnames(self, directory):
        dirnames = [directory]
        while directory and directory != os.path.dirname(directory):
            directory = os.path.dirname(directory)
            dirnames.append(directory)
        return dirnames

    # git repos
    def is_git_repo(self, directory):
        git_dir = os.path.join(directory, '.git')
        return os.path.exists(git_dir) and os.path.isdir(git_dir)

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

    def get_repo(self, window=None, silent=True):
        if window:
            active_view = window.active_view()
            if active_view:
                active_view_repo = active_view.settings().get('git_repo')
                if active_view_repo:
                    return active_view_repo

            window_repo = self.get_window_setting(window, 'git_repo')
            if window_repo:
                return window_repo

            any_repos = self.git_repos_from_window(window)
            if len(any_repos) == 1:
                only_repo = any_repos.pop()
                self.set_window_setting(window, 'git_repo', only_repo)
                return only_repo

            if silent:
                return

            if any_repos:
                self.get_window().run_command('git_switch_repo')
            else:
                if sublime.ok_cancel_dialog(GIT_INIT_DIALOG, 'Initialize repository'):
                    self.get_window().run_command('git_init')

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

    URL = 'http://sublime-git.dk'
    LICENSE_POPUP = "SublimeGit Evaluation\n\nI hope you are enjoying SublimeGit. " +\
                    "If you are, please consider buying a license at http://sublimegit.net"

    def __license_popup(self):
        if sublime.ok_cancel_dialog(self.LICENSE_POPUP, 'Buy SublimeGit'):
            webbrowser.open(self.URL)

    def __check_license(self):
        seconds_since_start = (datetime.today() - Cmd.started_at).seconds
        seconds_since_popup = (datetime.today() - Cmd.last_popup_at).seconds if Cmd.last_popup_at else None

        if seconds_since_start < 15 * 60:
            return
        if seconds_since_popup is not None and seconds_since_popup < 60 * 60:
            return

        license = self.__get_license()
        if not license or not self.__validate_license(license):
            sublime.set_timeout(self.__license_popup, 0)
            Cmd.last_popup_at = datetime.today()

    # cmd helpers
    def _string(self, result):
        exit, stdout = result
        return stdout.strip()

    def _lines(self, result):
        exit, stdout = result
        stdout = stdout.rstrip()
        if not stdout:
            return []
        return stdout.split('\n')

    def _exit_code(self, result):
        exit, stdout = result
        return exit

    def clean_command(self, cmd):
        return [c for c in cmd if c]

    def startupinfo(self):
        startupinfo = None
        if hasattr(subprocess, 'STARTUPINFO'):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        return startupinfo

    # sync commands
    def cmd(self, cmd, stdin=None, cwd=None):
        if not cwd:
            cwd = self.get_repo(self.get_window(), silent=False)
            if not cwd:
                raise SublimeGitException("Could not find repo.")

        command = self.clean_command(cmd)
        try:
            logger.debug("cmd: %s", command)

            encoding = get_setting('encoding', 'utf-8')
            if stdin:
                stdin = stdin.encode(encoding)

            os.chdir(cwd)
            proc = subprocess.Popen(command,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    startupinfo=self.startupinfo())
            stdout, stderr = proc.communicate(stdin)

            logger.debug("out: (%s) %s", proc.returncode, [stdout[:100]])

            self.__check_license()

            return (proc.returncode, stdout.decode(encoding))
        except OSError, e:
            sublime.error_message(self.get_executable_error())
            raise SublimeGitException("Could not execute command: %s" % e)

    def cmd_string(self, *args, **kwargs):
        return self._string(self.cmd(*args, **kwargs))

    def cmd_lines(self, *args, **kwargs):
        return self._lines(self.cmd(*args, **kwargs))

    def cmd_exit_code(self, *args, **kwargs):
        return self._lines(self.cmd(*args, **kwargs))

    # async commands
    def cmd_async(self, cmd, cwd=None, **callbacks):
        if not cwd:
            cwd = self.get_repo(self.get_window(), silent=False)
            if not cwd:
                return

        command = self.clean_command(cmd)

        def async_inner(cmd, cwd, on_data=None, on_complete=None, on_error=None, on_exception=None):
            try:
                logger.debug('async-cmd: %s', cmd)

                os.chdir(cwd)
                proc = subprocess.Popen(cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        startupinfo=self.startupinfo())

                for line in iter(proc.stdout.readline, ''):
                    logger.debug('async-out: %s', line.strip())
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

            except OSError, e:
                logger.debug('async-exception: %s' % e)
                if callable(on_exception):
                    sublime.set_timeout(partial(on_exception, e), 0)

        thread = threading.Thread(target=partial(async_inner, command, cwd, **callbacks))
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
    __executable__ = 'git'
    __bin__ = ['git']
    __opts__ = ['--no-pager']


class GitFlowCmd(Cmd):
    __executable__ = 'git_flow'
    __bin__ = ['git-flow']


class HubCmd(Cmd):
    __executable__ = 'hub'
    __bin__ = ['hub']
