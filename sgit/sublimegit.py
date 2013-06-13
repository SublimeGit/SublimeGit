# coding: utf-8
import re
import logging
import webbrowser
from functools import partial

import sublime
from sublime_plugin import WindowCommand

from .cmd import Cmd
from .util import noop, get_settings, SETTINGS_FILE


logger = logging.getLogger(__name__)


SUBLIMEGIT_LICENSE_EXISTS = ("You already have a license installed. "
                             "Do you want to overwrite it?\n\n"
                             "Email:\n  %s\n"
                             "License key:\n  %s")


class SublimeGitInstallLicenseCommand(WindowCommand, Cmd):
    """
    Install a SublimeGit license.

    You will be asked to enter your email address and license key. If there
    is already a license installed, you will be asked if you want to overwrite
    it. Press escape at any time to cancel.

    .. note::

        This command only does basic validation on your license. If the
        evaluation popup keeps appearing, then there is an issue with your license,
        and you should contact support@sublimegit.net

    """

    def _show_email_input(self, initial):
        self.window.show_input_panel('Email:', initial, self.on_email, noop, noop)

    def _show_license_input(self, email, initial=''):
        self.window.show_input_panel('License Key:', initial, partial(self.on_key, email), noop, noop)

    def run(self):
        settings = get_settings()

        email = settings.get('email', '')
        key = settings.get('product_key')

        print email
        print key

        if email and key:
            msg = SUBLIMEGIT_LICENSE_EXISTS % (email, key)
            if not sublime.ok_cancel_dialog(msg, 'Overwrite'):
                return

        self._show_email_input(email)

    def on_email(self, email):
        email = email.strip()

        if not email:
            sublime.error_message("Please provide an email, or press escape to cancel.")
            self._show_email_input(email)
            return

        if '@' not in email:
            sublime.error_message("Are you sure that's a valid email?")
            self._show_email_input(email)
            return

        self._show_license_input(email)

    def on_key(self, email, key):
        key = key.strip()

        if not key:
            sublime.error_message("Please provide a license key, or press escape to cancel.")
            self._show_license_input(email)
            return

        if len(key) != 32 or re.search(r'[^0-9a-f]', key) is not None:
            sublime.error_message("Invalid key format. Please double check the license key.")
            self._show_license_input(email, key)
            return

        settings = get_settings()
        settings.set('email', email)
        settings.set('product_key', key)

        sublime.save_settings(SETTINGS_FILE)
        sublime.message_dialog("Thank you. Your license has been installed.")


class SublimeGitBuyLicenseCommand(WindowCommand):
    """
    Buy SublimeGit. We love you!
    """

    URL = "https://sublimegit.net/buy?utm_source=sublimegit&utm_medium=command&utm_campaign=buy"

    def run(self):
        webbrowser.open(self.URL)


class SublimeGitDocumentationCommand(WindowCommand):
    """
    Open a webbrowser to the online SublimeGit documentation.
    """

    URL = "https://docs.sublimegit.net/?utm_source=sublimegit&utm_medium=command&utm_campaign=docs"

    def run(self):
        webbrowser.open(self.URL)
