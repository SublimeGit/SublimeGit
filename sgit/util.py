# coding: utf-8
from os import path, getenv
from contextlib import contextmanager

import sublime


# Misc helpers
def maybe_int(val):
    try:
        return int(val)
    except ValueError:
        return val


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


def scroll_to_bottom(view):
    view.show(view.size())


def find_view(window, title):
    views = [v for v in window.views() if v.name() == title]
    if views:
        return views[0]


def find_or_create_view(window, title, syntax=None, scratch=False, read_only=False, settings=None):
    view = find_view(window, title)
    if not view:
        view = window.new_file()
        view.set_name(title)
        if syntax:
            view.set_syntax_file(syntax)
        view.set_scratch(scratch)
        view.set_read_only(read_only)
        if settings:
            for s, v in settings.items():
                view.settings().set(s, v)
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


# CWD helpers

def find_cwd(window):
    if window:
        view = window.active_view()
        if view and view.file_name():
            return path.realpath(path.dirname(view.file_name()))
        elif window.folders():
            return window.folders()[0]
    #elif view and view.settings().has('git_repo_dir'):
    #    return view.settings().get('git_repo_dir')
    return None


# Directory helpers

def abbreviate_dir(dirname):
    user_dir = getenv('HOME')
    if dirname.startswith(user_dir):
        return dirname.replace(user_dir, '~', 1)
    return dirname


def find_possible_roots(directory):
    while directory and path.basename(directory):
        yield path.join(directory, '.git')
        directory = path.dirname(directory)
    if directory:
        yield path.join(directory, '.git')


def find_repo_dir(directory):
    for d in find_possible_roots(directory):
        if path.exists(d) and path.isdir(d):
            return path.dirname(d)


# settings helpers

def get_settings():
    return sublime.load_settings("SublimeGit.sublime-settings")


def get_setting(key, default=None):
    return get_settings().get(key, default)


def get_executable(key, default=None):
    return get_setting('git_executables', {}).get(key, default)
