# coding: utf-8
import os
import re
import webbrowser
try:
    from xml.etree import cElementTree as ET
except:
    from xml.etree import ElementTree as ET

import sublime
from sublime_plugin import WindowCommand

from .util import get_setting
from .cmd import GitCmd


MANPAGE_RE = re.compile(r'\(\d\) Manual Page\s*')


class GitHelpCommand(WindowCommand, GitCmd):

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

    def run(self):
        doc_path = self.git_string(['--html-path'], cwd=os.path.realpath(''))
        if not os.path.exists(doc_path):
            sublime.error_message('Directory %s does not exist. Have you deleted the git documentation?' % doc_path)
            return

        use_fancy = get_setting('git_use_fancy_help', True)
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

    def run(self):
        version = self.git_string(['--version'], cwd=os.path.realpath(''))
        sublime.error_message("You have %s" % version)
