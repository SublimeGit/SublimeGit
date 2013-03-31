# coding: utf-8
import re
import logging


logger = logging.getLogger(__name__)


class GitBranchHelper(object):

    def get_current_branch(self):
        branch = self.git_string(['symbolic-ref', '-q', 'HEAD'])
        return branch[11:] if branch.startswith('refs/heads/') else branch

    def get_branches(self):
        lines = self.git_lines(['branch', '--no-color', '--no-column'])

        branches = []
        for line in lines:
            current = line.startswith('*')
            name = line[2:].strip()
            branches.append((current, name))

        return branches


class GitRemoteHelper(GitBranchHelper):

    def get_remotes(self):
        return self.git_lines(['remote', '-v'])

    def get_remote_names(self, remotes):
        names = set()
        for r in remotes:
            name, url, action = r.split()
            names.append(name)
        return sorted(list(names))

    def format_quick_remotes(self, remotes):
        data = {}
        for r in remotes:
            name, url, action = r.split()
            data.setdefault(name, {})[action] = "%s %s" % (url, action)
        choices = []
        for remote, urls in data.items():
            choices.append([remote, urls.get('(fetch)', None), urls.get('(push)', None)])
        return choices

    def get_remote(self, branch):
        return self.git_string(['config', 'branch.%s.remote' % branch])

    def get_current_remote(self):
        return self.get_remote(self.get_current_branch())

    def get_current_remote_or_origin(self):
        return self.get_remote_or_origin(self.get_current_branch())

    def get_remote_url(self, remote):
        return self.git_string(['config', 'remote.%s.url' % remote])

    def get_merge_branch(self, branch):
        return self.git_string(['config', 'branch.%s.merge' % branch])

    def get_remote_or_origin(self, branch=None):
        if branch:
            remote = self.git_string(['config', 'branch.%s.remote' % branch])
            if remote:
                return remote
        origin = self.git_string(['config', 'remote.origin.url'])
        if origin:
            return 'origin'
        return None

    def get_remote_branches(self, remote):
        branches = [b.strip() for b in self.git_lines(['branch', '-r'])]
        return [b for b in branches if b.startswith(remote + '/')]

    def format_quick_branches(self, branches):
        choices = []
        for b in branches:
            branch = b.split('/', 1)[1]
            choices.append([branch, b])
        return choices


class GitStashHelper(object):

    STASH_RE = re.compile(r'^stash@\{(.*)\}:\s*(.*)')

    def get_stashes(self):
        stashes = []
        output = self.git_lines(['stash', 'list'])
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

    def has_changes(self):
        return self.has_staged_changes() or self.has_unstaged_changes()

    def has_staged_changes(self):
        return self.git_exit_code(['diff', '--exit-code', '--quiet', '--cached']) != 0

    def has_unstaged_changes(self):
        return self.git_exit_code(['diff', '--exit-code', '--quiet']) != 0

    def get_files_status(self):
        untracked, unstaged, staged = [], [], []
        status = self.git_lines(['status', '--porcelain', '--untracked-files=all'])
        for l in status:
            state, filename = l[0:2], l[3:]
            index, worktree = state
            filename = filename.strip('"')
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


class GitDiffHelper(object):

    def get_diff(self, path=None, cached=False):
        args = ['diff', '--cached' if cached else None]
        if path:
            args.extend(['--', path])
        return self.git_string(args)


class GitShowHelper(object):

    def get_show(self, obj):
        return self.git_string(['show', '--format=medium', '--no-color', obj])


class GitLogHelper(object):

    NULL = u'\u0000'
    GIT_QUICK_LOG_FORMAT = ('%s%n'   # subject\n
                            '%H%n'   # sha1\n
                            '%an%n'  # author name\n
                            '%aE%n'  # author email\n
                            '%ad%n'  # auth date\n
                            '%ar')   # auth date relative

    def get_quick_log(self, path=None):
        cmd = ['log', '--no-color', '-z', '--date=local', '--format=%s' % self.GIT_QUICK_LOG_FORMAT]
        if path:
            cmd.extend(['--', path])
        out = self.git_string(cmd)
        return [s.split('\n') for s in out.split(self.NULL) if s]

    def format_quick_log(self, path=None):
        log = self.get_quick_log(path)
        hashes = [l[1] for l in log]
        choices = []
        for subject, sha, name, email, dt, reldt in log:
            choices.append([subject, '%s by %s <%s>' % (sha[0:8], name, email), '%s (%s)' % (reldt, dt)])
        return hashes, choices
