# coding: utf-8
import os
import re
import logging
import webbrowser
try:
    from xml.etree import cElementTree as ET
except:
    from xml.etree import ElementTree as ET

import sublime
from sublime_plugin import WindowCommand

from .util import get_setting
from .cmd import GitCmd


logger = logging.getLogger('SublimeGit.help')

MANPAGE_RE = re.compile(r'\(\d\) Manual Page\s*')


class GitHelpCommand(WindowCommand, GitCmd):
    """
    Search through installed Git documentation.

    Every standard install of git contains a full set of manual pages
    in both text and html formats. This commands presents a list
    of available documentation in a quick bar to allow for easy access.

    When a document has been selected, a webbrowser will be opened to
    show the help file. To abort the list without opening the document,
    press ``esc``.

    .. :setting git_help_format: Text or html?

    :setting git_help_fancy_list: If set to ``true``, SublimeGit will
        try to parse the help document to show a nicer list containing
        a small excerpt from each document. This has a small performance
        cost the first time the list is generated. Set to ``false`` to
        fall back to simple format. Default: ``true``

    :setting git_help_html_path: If set to a directory, SublimeGit will
        look in the given directory for git help files. Set to ``null``
        to make SublimeGit auto-detect the location of the help files.

    .. note::

        To find the location the installed documentation, you can
        execute::

            $ git --html-path
            /usr/local/Cellar/git/1.7.11.3/share/doc/git-doc

    """

    def get_doc_files(self, doc_path):
        files = []
        for f in os.listdir(doc_path):
            if not f.endswith('.html'):
                continue
            if f == 'index.html':
                continue
            files.append(os.path.join(doc_path, f))
        return files

    def format_choices(self, doc_files, fancy=False):
        formatter = self.format_fancy if fancy else self.format_plain

        choices = []
        for f in doc_files:
            url = 'file://%s' % f
            choice = formatter(f)
            if choice:
                choices.append((choice, url))

        return sorted(choices)

    def format_fancy(self, filename):
        # deal wth a couple of special files
        if filename.endswith('everyday.html'):
            return [u'Everyday GIT With 20 Commands Or So',
                    u'Individual Developer (Standalone) commands are essential for anybody ' +
                    'who makes a commit, even for somebody who works alone.']
        elif filename.endswith('user-manual.html'):
            return [u"Git User's Manual",
                    u"Git is a fast distributed revision control system."]

        title = os.path.basename(filename)[:-5]
        text = '[no summary]'

        try:
            root = ET.parse(filename).getroot()
        except Exception:
            return [title, '[could not parse file]']

        h1 = root.find(".//{http://www.w3.org/1999/xhtml}h1")
        p = root.find(".//{http://www.w3.org/1999/xhtml}p")

        if h1 is not None and p is not None:
            if h1.text and p.text:
                title = h1.text
                content = p.text

                if MANPAGE_RE.search(title):
                    # We are dealing with a manpage
                    title = MANPAGE_RE.sub('', title)
                    _, secondline = content.split('\n', 1)
                    text = secondline.strip().replace('\n', ' ')
                else:
                    text = content.replace('\n', ' ').strip()

        if len(text) > 100:
            text = text[:100]

        return [title, text]

    def format_plain(self, filename):
        basename = os.path.basename(filename)
        noext = basename[:-5]
        text = noext[4:] if noext.startswith('git-') else noext

        return text

    def get_doc_path(self):
        git_html_path = get_setting('git_help_html_path', None)
        if git_html_path:
            logger.debug('Got git html path from settings: %s', git_html_path)
            return git_html_path
        else:
            git_html_path = self.git_string(['--html-path'], cwd=os.path.realpath(''))
            logger.debug('Got git html path from git: %s', git_html_path)
            return git_html_path

    def run(self):
        doc_path = self.get_doc_path()
        if not os.path.exists(doc_path):
            sublime.error_message('Directory %s does not exist. Have you deleted the git documentation?' % doc_path)
            return

        use_fancy = get_setting('git_help_fancy_list', True)
        if hasattr(self, '_use_fancy'):
            if use_fancy != self._use_fancy:
                self._choices = None

        self._use_fancy = use_fancy

        if not getattr(self, '_choices', None):
            doc_files = self.get_doc_files(doc_path)
            self._choices = self.format_choices(doc_files, fancy=use_fancy)

        def on_done(idx):
            if idx != -1:
                text, url = self._choices[idx]
                webbrowser.open(url)

        self.window.show_quick_panel([t for t, u in self._choices], on_done)


class GitVersionCommand(WindowCommand, GitCmd):
    """
    Shows the version of git which is installed

    This corresponds to running::

        $ git --version
        git version 1.7.11.3

    """

    def run(self):
        version = self.git_string(['--version'], cwd=os.path.realpath(''))
        sublime.message_dialog("You have %s" % version)
