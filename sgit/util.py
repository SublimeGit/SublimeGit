# coding: utf-8
from os import path
from contextlib import contextmanager
import logging

import sublime


logger = logging.getLogger(__name__)


# Callback helpers
def noop(*args, **kwargs):
    pass


# View helpers
@contextmanager
def ensure_writeable(view):
    read_only = view.is_read_only()
    view.set_read_only(False)
    yield
    view.set_read_only(read_only)


def read_view(view):
    return view.substr(sublime.Region(0, view.size()))


def write_view(view, content):
    edit = view.begin_edit()
    if view.size() > 0:
        view.erase(edit, sublime.Region(0, view.size()))
    view.insert(edit, 0, content)
    view.end_edit(edit)


def append_view(view, content, scroll=False):
    edit = view.begin_edit()
    view.insert(edit, view.size(), content)
    view.end_edit(edit)
    if scroll:
        view.show(view.size())


def find_view_by_settings(window, **kwargs):
    for view in window.views():
        s = view.settings()
        matches = [s.get(k) == v for k, v in kwargs.items()]
        if all(matches):
            return view


# Panel helpers
def create_panel(window, name, content=None, show=True):
    panel = window.get_output_panel(name)
    if content:
        write_view(panel, content)
    if show:
        show_panel(window, name)
    return panel


def show_panel(window, name):
    window.run_command('show_panel', {'panel': 'output.%s' % name})


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


# Directory helpers

def abbreviate_dir(dirname):
    user_dir = path.expanduser('~')
    if dirname.startswith(user_dir):
        return '~' + dirname[len(user_dir):]
    return dirname


# settings helpers

def get_settings():
    return sublime.load_settings("SublimeGit.sublime-settings")


def get_setting(key, default=None):
    return get_settings().get(key, default)


def get_executable(key, default=None):
    return get_setting('git_executables', {}).get(key, default)
