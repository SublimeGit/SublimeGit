# coding: utf-8
import sys
from os import path
import logging

import sublime
from sublime_plugin import TextCommand


logger = logging.getLogger('SublimeGit.util')

# Constants

SETTINGS_FILE = 'SublimeGit.sublime-settings'


# Compatibility

PY2 = sys.version_info[0] == 2

if PY2:
    text_type = unicode
    string_types = (str, unicode)
    unichr = unichr
else:
    text_type = str
    string_types = (str,)
    unichr = chr


# Callback helpers

def noop(*args, **kwargs):
    pass


# View helpers

def find_view_by_settings(window, **kwargs):
    for view in window.views():
        s = view.settings()
        matches = [s.get(k) == v for k, v in list(kwargs.items())]
        if all(matches):
            return view


# progress helper

class StatusSpinner(object):

    SIZE = 10  # 10 equal signs
    TIME = 50  # 50 ms delay

    def __init__(self, thread, msg):
        self.counter = 0
        self.direction = 1
        self.msg = msg
        self.thread = thread

    def progress(self):
        if not self.thread.is_alive():
            sublime.status_message('')
            return

        left, right = self.counter, (self.SIZE - 1 - self.counter)
        self.counter += self.direction
        if self.counter in (0, self.SIZE - 1):
            self.direction *= -1

        status = "[%s=%s] %s" % (' ' * left, ' ' * right, self.msg)

        sublime.status_message(status)
        sublime.set_timeout(self.progress, self.TIME)

    def start(self):
        self.thread.start()
        sublime.set_timeout(self.progress, 0)


# Panel Helper

class GitPanelWriteCommand(TextCommand):

    def is_visible(self):
        return False

    def run(self, edit, content=''):
        self.view.set_read_only(False)
        if self.view.size() > 0:
            self.view.erase(edit, sublime.Region(0, self.view.size()))
        self.view.insert(edit, 0, content)
        self.view.set_read_only(True)


class GitPanelAppendCommand(TextCommand):

    def is_visible(self):
        return False

    def run(self, edit, content='', scroll=False):
        self.view.insert(edit, self.view.size(), content)
        if scroll:
            self.view.show(self.view.size())


# Directory helpers

def get_user_dir():
    user_dir = ''
    try:
        user_dir = path.expanduser(u'~')
    except:
        try:
            user_dir = path.expanduser('~')
        except:
            pass

    if PY2 and isinstance(user_dir, str):
        try:
            user_dir = user_dir.decode('utf-8')
        except:
            pass

    return user_dir


def abbreviate_dir(dirname):
    user_dir = get_user_dir()
    try:
        if dirname.startswith(user_dir):
            dirname = u'~%s' % dirname[len(user_dir):]
    except:
        pass
    return dirname


# settings helpers

def get_settings():
    return sublime.load_settings(SETTINGS_FILE)


def get_setting(key, default=None):
    return get_settings().get(key, default)


def get_executable(key, default=None):
    return get_setting('git_executables', {}).get(key, default)
