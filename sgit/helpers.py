# coding: utf-8
import re
import os
import logging
import sublime

from .util import get_setting


logger = logging.getLogger('SublimeGit.helpers')


GIT_INIT_DIALOG = ("Could not find any git repositories based on the open files and folders. "
                   "Do you want to initialize a repository?")


class GitRepoHelper(object):
    # fallback repos for windows, indexed by id
    windows = {}

    # working dir remake
    def get_dir_from_view(self, view=None):
        d = None
        if view is not None and view.file_name():
            d = os.path.realpath(os.path.dirname(view.file_name()))
            logger.info('get_dir_from_view(view=%s): %s', view.id(), d)
        return d

    def get_dirs_from_window_folders(self, window=None):
        dirs = set()
        if window is not None:
            dirs = set(f for f in window.folders())
            logger.info('get_dirs_from_window_folders(window=%s): %s', window.id(), dirs)
        return dirs

    def get_dirs_from_window_views(self, window=None):
        dirs = set()
        if window is not None:
            view_dirs = [self.get_dir_from_view(v) for v in window.views()]
            dirs = set(d for d in view_dirs if d)
            logger.info('get_dirs_from_window_views(window=%s): %s', window.id(), dirs)
        return dirs

    def get_dirs(self, window=None):
        dirs = set()
        if window is not None:
            dirs |= self.get_dirs_from_window_folders(window)
            dirs |= self.get_dirs_from_window_views(window)
            logger.info('get_dirs(window=%s): %s', window.id(), dirs)
        return dirs

    def get_dirs_prioritized(self, window=None):
        dirs = list()
        if window is not None:
            all_dirs = self.get_dirs(window)
            active_view_dir = self.get_dir_from_view(window.active_view())
            if active_view_dir:
                dirs.append(active_view_dir)
                all_dirs.discard(active_view_dir)
            for d in sorted(list(all_dirs), key=lambda x: len(x), reverse=True):
                dirs.append(d)
            logger.info('get_dirs_prioritized(window=%s): %s', window.id(), dirs)
        return dirs

    # path walking
    def all_dirnames(self, directory):
        dirnames = [directory]
        while directory and directory != os.path.dirname(directory):
            directory = os.path.dirname(directory)
            dirnames.append(directory)

        logger.info('all_dirs(directory=%s): %s', directory, dirnames)
        return dirnames

    # git repos
    def is_git_repo(self, directory):
        git_dir = os.path.join(directory, '.git')
        return os.path.exists(git_dir)

    def first_git_repo(self, directory):
        # check the first directory and exit fast
        if self.is_git_repo(directory):
            return directory

        # check up the tree
        while directory and directory != os.path.dirname(directory):
            directory = os.path.dirname(directory)
            if self.is_git_repo(directory):
                return directory

        # No repos
        return None

    def find_git_repos(self, directories):
        repos = set()
        for directory in directories:
            for dirname in self.all_dirnames(directory):
                if self.is_git_repo(dirname):
                    repos.add(dirname)
        return repos

    def git_repos_from_window(self, window=None):
        repos = set()
        if window is not None:
            dirs = self.get_dirs_prioritized(window)
            for repo in self.find_git_repos(dirs):
                repos.add(repo)
        return repos

    def git_repo_from_view(self, view=None):
        repo = None
        if view is not None:
            view_dir = self.get_dir_from_view(view)
            if view_dir:
                repo = self.first_git_repo(view_dir)
        return repo

    def get_repo(self, silent=False):
        repo = None

        if hasattr(self, 'view'):
            repo = self.get_repo_from_view(self.view, silent=silent)
            if self.view.window() and not repo:
                repo = self.get_repo_from_window(self.view.window(), silent=silent)
        elif hasattr(self, 'window'):
            repo = self.get_repo_from_window(self.window, silent=silent)

        return repo

    def get_repo_from_view(self, view=None, silent=True):
        if view is None:
            return

        # first try the view settings (for things like status, diff, etc)
        view_repo = view.settings().get('git_repo')
        if view_repo:
            logger.info('get_repo_from_view(view=%s, silent=%s): %s (view settings)', view.id(), silent, view_repo)
            return view_repo

        # else try the given view file
        file_repo = self.git_repo_from_view(view)
        if file_repo:
            logger.info('get_repo(window=%s, silent=%s): %s (file)', view.id(), silent, file_repo)
            return file_repo

    def get_repo_from_window(self, window=None, silent=True):
        if not window:
            logger.info('get_repo_from_window(window=%s, silent=%s): None (no window)', None, silent)
            return

        active_view = window.active_view()
        if active_view is not None:
            # if the active view has a setting, use that
            active_view_repo = active_view.settings().get('git_repo')
            if active_view_repo:
                logger.info('get_repo_from_window(window=%s, silent=%s): %s (view settings)', window.id(), silent, active_view_repo)
                return active_view_repo

            # if the active view has a filename, use that
            active_file_repo = self.git_repo_from_view(active_view)
            if active_file_repo:
                logger.info('get_repo_from_window(window=%s, silent=%s): %s (active file)', window.id(), silent, active_file_repo)
                return active_file_repo

        # find all possible repos
        any_repos = self.git_repos_from_window(window)
        window_repo = self.get_window_repository(window)

        # if there is only one repository, use that
        if len(any_repos) == 1:
            only_repo = any_repos.pop()
            logger.info('get_repo_from_window(window=%s, silent=%s): %s (only repo)', window.id(), silent, only_repo)
            return only_repo
        elif len(any_repos) > 1 and window_repo:
            logger.info('get_repo_from_window(window=%s, silent=%s): %s (window repo)', window.id(), silent, window_repo)
            return window_repo

        if silent:
            logger.info('get_repo_from_window(window=%s, silent=%s): None (silent)', window.id(), silent)
            return

        if any_repos:
            window.run_command('git_switch_repo')
        else:
            if sublime.ok_cancel_dialog(GIT_INIT_DIALOG, 'Initialize repository'):
                window.run_command('git_init')

    def set_window_repository(self, window, repo):
        GitRepoHelper.windows[window.id()] = repo

    def get_window_repository(self, window):
        return GitRepoHelper.windows.get(window.id())


class GitBranchHelper(object):

    def get_current_branch(self, repo):
        branch = self.git_string(['symbolic-ref', '-q', 'HEAD'], cwd=repo)
        return branch[11:] if branch.startswith('refs/heads/') else branch

    def get_branches(self, repo, remotes=False):
        lines = self.git_lines(['branch', '--list', '--no-color', '--remotes' if remotes else None], cwd=repo)

        branches = []
        for line in lines:
            current = line.startswith('*')
            nameparts = line[2:].split(' -> ')
            name = nameparts[1] if len(nameparts) == 2 else nameparts[0]
            branches.append((current, name))

        return branches


class GitRemoteHelper(GitBranchHelper):

    def get_remotes(self, repo):
        return self.git_lines(['remote', '-v'], cwd=repo)

    def get_remote_names(self, remotes):
        names = set()
        for r in remotes:
            name, right = r.split('\t', 1)
            url, action = right.rsplit(' ', 1)
            names.append(name)
        return sorted(list(names))

    def format_quick_remotes(self, remotes):
        data = {}
        for r in remotes:
            name, right = r.split('\t', 1)
            url, action = right.rsplit(' ', 1)
            data.setdefault(name, {})[action] = "%s %s" % (url, action)
        choices = []
        for remote, urls in list(data.items()):
            choices.append([remote, urls.get('(fetch)', None), urls.get('(push)', None)])
        return choices

    def get_remote_url(self, repo, remote):
        return self.git_string(['config', 'remote.%s.url' % remote], cwd=repo)

    def get_branch_upstream(self, repo, branch):
        return (self.get_branch_remote(repo, branch), self.get_branch_merge(repo, branch))

    def get_branch_remote(self, repo, branch):
        return self.git_string(['config', 'branch.%s.remote' % branch], cwd=repo)

    def get_branch_merge(self, repo, branch):
        return self.git_string(['config', 'branch.%s.merge' % branch], cwd=repo)

    def get_remote_branches(self, repo, remote):
        branches = [b for _, b in self.get_branches(repo, remotes=True)]
        return [b for b in branches if b.startswith(remote + '/')]

    def format_quick_branches(self, branches):
        choices = []
        for b in branches:
            branch = b.split('/', 1)[1]
            choices.append([branch, b])
        return choices


class GitStashHelper(object):

    STASH_RE = re.compile(r'^stash@\{(.*)\}:\s*(.*)')

    def get_stashes(self, repo):
        stashes = []
        output = self.git_lines(['stash', 'list'], cwd=repo)
        for line in output:
            match = self.STASH_RE.match(line)
            if match:
                stashes.append((match.group(1), match.group(2)))
        return stashes


class GitErrorHelper(object):

    def format_error_message(self, msg):
        if msg.startswith('error: '):
            msg = msg[7:]
        elif msg.lower().startswith('Note: '):
            msg = msg[6:]
        if msg.endswith('Aborting\n'):
            msg = msg.rstrip()[:-8]
        return msg


class GitStatusHelper(object):

    def file_in_git(self, repo, filename):
        return self.git_exit_code(['ls-files', filename, '--error-unmatch'], cwd=repo) == 0

    def has_changes(self, repo):
        return self.has_staged_changes(repo) or self.has_unstaged_changes(repo)

    def has_staged_changes(self, repo):
        return self.git_exit_code(['diff', '--exit-code', '--quiet', '--cached'], cwd=repo) != 0

    def has_unstaged_changes(self, repo):
        return self.git_exit_code(['diff', '--exit-code', '--quiet'], cwd=repo) != 0

    # def get_porcelain_status(self, repo):
    #     mode = self.get_untracked_mode()
    #     cmd = ['status', '--porcelain', ('--untracked-files=%s' % mode) if mode else None]
    #     return self.git_lines(cmd, cwd=repo)

    def get_porcelain_status(self, repo):
        mode = self.get_untracked_mode()
        cmd = ['status', '-z', ('--untracked-files=%s' % mode) if mode else None]

        output = self.git_string(cmd, cwd=repo, strip=False)
        rows = output.split('\x00')
        lines = []
        idx = 0
        while idx < len(rows):
            row = rows[idx]
            if row and not row.startswith('#'):
                status, filename = row[:2], row[3:]
                if status[0] == 'R':
                    lines.append("%s %s -> %s" % (status, rows[idx + 1], filename))
                    idx += 1
                else:
                    lines.append("%s %s" % (status, filename))
            idx += 1
        return lines

    def get_files_status(self, repo):
        untracked, unstaged, staged = [], [], []
        status = self.get_porcelain_status(repo)
        for l in status:
            state, filename = l[:2], l[3:]
            index, worktree = state
            if state in ('DD', 'AU', 'UD', 'UA', 'DU', 'AA', 'UU'):
                logger.warning("unmerged WTF: %s, %s", state, filename)
            elif state == '??':
                untracked.append(('?', filename))
            elif state == '!!':
                continue
            else:
                if worktree != ' ':
                    unstaged.append((worktree, filename))
                if index != ' ':
                    staged.append((index, filename))
        return untracked, unstaged, staged

    def get_untracked_mode(self):
        # get untracked files mode
        setting = get_setting('git_status_untracked_files', 'all')

        mode = 'all'
        if setting == 'none':
            mode = 'no'
        elif setting == 'auto':
            mode = None
        return mode


class GitDiffHelper(object):

    def get_diff(self, repo, path=None, cached=False, unified=None):
        try:
            unified = int(unified)
        except:
            unified = None
        args = ['diff',
                '--cached' if cached else None,
                '--unified=%s' % unified if unified else None]
        if path:
            args.extend(['--', path])
        return self.git_string(args, cwd=repo, strip=False)


class GitShowHelper(object):

    def get_show(self, repo, obj):
        return self.git_string(['show', '--format=medium', '--no-color', obj], cwd=repo)


class GitLogHelper(object):

    GIT_QUICK_LOG_FORMAT = ('%s%x03'   # subject
                            '%H%x03'   # sha1
                            '%an%x03'  # author name
                            '%aE%x03'  # author email
                            '%ad%x03'  # auth date
                            '%ar'    # auth date relative
                            '%x04')

    def get_quick_log(self, repo, path=None, follow=False):
        cmd = ['log', '--no-color', '--date=local', '--format=%s' % self.GIT_QUICK_LOG_FORMAT]
        if follow:
            cmd.append('--follow')
        if path:
            cmd.extend(['--', path])
        out = self.git_string(cmd, cwd=repo, strip=False)

        lines = []
        for line in out.split(u'\u0004'):
            line = line.strip()
            if line:
                parts = line.split(u'\u0003')
                if len(parts) != 6:
                    raise Exception("The line %s splits to %s", line, parts)
                lines.append(parts)
        return lines

    def format_quick_log(self, log):
        hashes = [l[1] for l in log]
        choices = []
        for subject, sha, name, email, dt, reldt in log:
            choices.append([subject, '%s by %s <%s>' % (sha[0:8], name, email), '%s (%s)' % (reldt, dt)])
        return hashes, choices


class GitTagHelper(object):

    def get_tags(self, repo, annotate=True):
        if annotate:
            return self.git_lines(['tag', '--list', '-n1'], cwd=repo)
        else:
            return self.git_lines(['tag', '--list', '-n0', '--no-column'], cwd=repo)

    def format_quick_tags(self, tags):
        out = []
        for t in reversed(tags):
            tag, ann = t.split(' ', 1)
            out.append([tag, ann.strip()])
        return out
