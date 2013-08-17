# coding: utf-8
from functools import partial

import sublime
from sublime_plugin import WindowCommand

from .util import StatusSpinner, noop
from .cmd import GitCmd
from .helpers import GitTagHelper, GitErrorHelper


TAG_FORCE = u'The tag %s already exists. Do you want to overwrite it?'


class GitAddTagCommand(WindowCommand, GitTagHelper, GitErrorHelper, GitCmd):
    """
    Documentation coming soon.
    """

    def run(self, sign=False):
        repo = self.get_repo()
        if not repo:
            return

        tags = self.get_tags(repo, annotate=False)

        def on_done(name):
            name = name.strip()
            if not name:
                return

            if name in tags:
                if sublime.ok_cancel_dialog(TAG_FORCE % name, 'Overwrite'):
                    self.on_name(repo, sign, name, force=True)
            else:
                self.on_name(repo, sign, name)

        self.window.show_input_panel('Tag:', '', on_done, noop, noop)

    def on_name(self, repo, sign, name, force=False):
        def on_done(message):
            message = message.strip()
            if not message:
                if sign:
                    if sublime.ok_cancel_dialog('A signed tag requires a message.', 'Enter message'):
                        self.on_name(repo, sign, name, force)
                    return
                else:
                    message = None

            self.on_message(repo, sign, name, force, message)

        self.window.show_input_panel('Message:', '', on_done, noop, noop)

    def on_message(self, repo, sign, name, force, message=None):
        kind = None
        if sign:
            kind = '--sign'
        elif message:
            kind = '--annotate'

        # build command
        cmd = ['tag', kind, '--force' if force else None]
        if message:
            cmd += ['-F', '-']
        cmd += [name]

        # run command
        exit, stdout, stderr = self.git(cmd, cwd=repo, stdin=message)
        if exit == 0:
            if stdout:
                panel = self.window.get_output_panel('git-tag')
                panel.run_command('git_panel_write', {'content': stdout})
                self.window.run_command('show_panel', {'panel': 'output.git-tag'})
            else:
                sublime.status_message("Added tag %s" % name)
        else:
            sublime.error_message(self.format_error_message(stderr))


class GitTagCommand(WindowCommand, GitTagHelper, GitErrorHelper, GitCmd):
    """
    Documentation coming soon.
    """

    ADD_TAG = '+ Add tag'

    SHOW = 'Show'
    CHECKOUT = 'Checkout'
    VERIFY = 'Verify'
    DELETE = 'Delete'

    TAG_ACTIONS = [
        [SHOW, 'git show {tag}'],
        [CHECKOUT, 'git checkout tags/{tag}'],
        [VERIFY, 'git tag --verify {tag}'],
        [DELETE, 'git tag --delete {tag}'],
    ]

    ACTION_CALLBACKS = {
        SHOW: 'show_tag',
        CHECKOUT: 'checkout_tag',
        VERIFY: 'verify_tag',
        DELETE: 'delete_tag',
    }

    def run(self, repo=None):
        repo = repo or self.get_repo()
        if not repo:
            return

        tags = self.get_tags(repo)
        choices = self.format_quick_tags(tags)
        choices.append([self.ADD_TAG, 'Add a tag referencing the current commit.'])

        def on_done(idx):
            if idx != -1:
                tag = choices[idx][0]
                if tag == self.ADD_TAG:
                    self.window.run_command('git_add_tag')
                else:
                    sublime.set_timeout(partial(self.on_tag, repo, tag), 50)

        self.window.show_quick_panel(choices, on_done)

    def on_tag(self, repo, tag):
        choices = [[a, t.format(tag=tag)] for a, t in self.TAG_ACTIONS]

        def on_done(idx):
            if idx != -1:
                action = self.TAG_ACTIONS[idx][0]
                callback = self.ACTION_CALLBACKS.get(action)

                func = getattr(self, callback, None)
                if func:
                    func(repo, tag)

        self.window.show_quick_panel(choices, on_done)

    def reset(self, repo):
        def on_time():
            self.window.run_command('git_tag', {'repo': repo})
        sublime.set_timeout(on_time, 50)

    # callbacks

    def verify_tag(self, repo, tag):
        self.panel = self.window.get_output_panel('git-tag')
        self.panel_shown = False

        thread = self.git_async(['tag', '--verify', tag], cwd=repo, on_data=self.on_data)
        runner = StatusSpinner(thread, "Verifying %s" % tag)
        runner.start()
        self.reset(repo)

    def show_tag(self, repo, tag):
        self.window.run_command('git_show', {'repo': repo, 'obj': 'tags/%s' % tag})

    def delete_tag(self, repo, tag):
        exit, stdout, stderr = self.git(['tag', '--delete', tag], cwd=repo)
        if exit == 0:
            self.reset(repo)
        else:
            sublime.error_message(stderr)

    def checkout_tag(self, repo, tag):
        self.window.run_command('git_checkout_tag', {'repo': repo, 'tag': tag})

    # async helpers

    def on_data(self, d):
        if not self.panel_shown:
            self.window.run_command('show_panel', {'panel': 'output.git-tag'})
        self.panel.run_command('git_panel_append', {'content': d, 'scroll': True})
