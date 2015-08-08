# coding: utf-8
import sys
import logging
import webbrowser

import sublime
from sublime_plugin import WindowCommand

from . import __version__


logger = logging.getLogger('SublimeGit.sublimegit')


class SublimeGitVersionCommand(WindowCommand):
    """
    Show the currently installed version of SublimeGit.
    """

    def run(self):
        sublime.message_dialog("You have SublimeGit %s" % __version__)


class SublimeGitDocumentationCommand(WindowCommand):
    """
    Open a webbrowser to the online SublimeGit documentation.
    """

    URL = "https://docs.sublimegit.net/?utm_source=st%s&utm_medium=command&utm_campaign=docs"

    def run(self):
        url = self.URL % sys.version_info[0]
        webbrowser.open(url)
