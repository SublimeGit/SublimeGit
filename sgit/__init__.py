# coding: utf-8
import os

import sublime
from sublime_plugin import EventListener


SUBLIME_GIT = os.path.join(sublime.packages_path(), 'SublimeGit/SublimeGit.py')


class DebugReloader(EventListener):

    def on_post_save(self, view):
        if "sgit/" in view.file_name():
            window = view.window()
            window.open_file(SUBLIME_GIT)
            window.run_command('save')
            window.focus_view(view)
