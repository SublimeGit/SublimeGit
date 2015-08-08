# coding: utf-8
import os
import logging
import threading
from functools import partial

import sublime
from sublime_plugin import WindowCommand, TextCommand, EventListener

from .util import abbreviate_dir, find_view_by_settings, noop, get_setting, get_executable
from .cmd import GitCmd
from .helpers import GitStatusHelper, GitRemoteHelper, GitStashHelper, GitErrorHelper


logger = logging.getLogger('SublimeGit.status')

GOTO_DEFAULT = 'file:1'

GIT_STATUS_VIEW_TITLE_PREFIX = '*git-status*: '
GIT_STATUS_VIEW_SYNTAX = 'Packages/SublimeGit/syntax/SublimeGit Status.tmLanguage'
GIT_STATUS_VIEW_SETTINGS = {
    'translate_tabs_to_spaces': False,
    'draw_white_space': 'none',
    'word_wrap': False,
    'git_status': True,
}

STASHES = "stashes"
UNTRACKED_FILES = "untracked_files"
UNSTAGED_CHANGES = "unstaged_changes"
STAGED_CHANGES = "staged_changes"
CHANGES = "changes"  # pseudo-section to ignore staging area

SECTIONS = {
    STASHES: 'Stashes:\n',
    UNTRACKED_FILES: 'Untracked files:\n',
    UNSTAGED_CHANGES: 'Unstaged changes:\n',
    STAGED_CHANGES: 'Staged changes:\n',
    CHANGES: 'Changes:\n',
}

SECTION_ORDER = (
    STASHES,
    UNTRACKED_FILES,
    UNSTAGED_CHANGES,
    STAGED_CHANGES,
    CHANGES,
)


SECTION_SELECTOR_PREFIX = 'meta.git-status.'

STATUS_LABELS = {
    ' ': 'Unmodified',
    'M': 'Modified  ',
    'A': 'Added     ',
    'D': 'Deleted   ',
    'R': 'Renamed   ',
    'C': 'Copied    ',
    'U': 'Unmerged  ',
    '?': 'Untracked ',
    '!': 'Ignored   ',
    'T': 'Typechange'
}

GIT_WORKING_DIR_CLEAN = "Nothing to commit (working directory clean)"

GIT_STATUS_HELP = """
# Movement:
#    r = refresh status
#    1-5 = jump to section
#    n = next item, N = next section
#    p = previous item, P = previous section
#
# Staging:
#    s = stage file/section, S = stage all unstaged files
#    ctrl+shift+s = stage all unstaged and untracked files
#    u = unstage file/section, U = unstage all files
#    backspace = discard file/section, shift+backspace = discard everything
#
# Commit:
#    c = commit, C = commit -a (add unstaged)
#    ctrl+shift+c = commit --amend (amend previous commit)
#
# Other:
#    i = ignore file, I = ignore pattern
#    enter = open file
#    d = view diff
#
# Stashes:
#    a = apply stash, A = pop stash
#    z = create stash, Z = create stash including untracked files
#    backspace = discard stash"""


class GitStatusBuilder(GitCmd, GitStatusHelper, GitRemoteHelper, GitStashHelper):

    def build_status(self, repo):
        branch = self.get_current_branch(repo)
        remote = self.get_branch_remote(repo, branch)
        remote_url = self.get_remote_url(repo, remote)

        abbrev_dir = abbreviate_dir(repo)

        head_rc, head, _ = self.git(['log', '--max-count=1', '--abbrev-commit', '--pretty=oneline'], cwd=repo)

        status = ""
        if remote:
            status += "Remote:   %s @ %s\n" % (remote, remote_url)
        status += "Local:    %s %s\n" % (branch if branch else '(no branch)', abbrev_dir)
        status += "Head:     %s\n" % ("nothing committed (yet)" if head_rc != 0 else head)
        status += "\n"

        # update index
        self.git_exit_code(['update-index', '--refresh'], cwd=repo)

        status += self.build_stashes(repo)
        status += self.build_files_status(repo)

        if get_setting('git_show_status_help', True):
            status += GIT_STATUS_HELP

        return status

    def build_stashes(self, repo):
        status = ""

        stashes = self.get_stashes(repo)
        if stashes:
            status += SECTIONS[STASHES]
            for name, title in stashes:
                status += "\t%s: %s\n" % (name, title)
            status += "\n"

        return status

    def build_files_status(self, repo):
        # get status
        status = ""
        untracked, unstaged, staged = self.get_files_status(repo)

        if not untracked and not unstaged and not staged:
            status += GIT_WORKING_DIR_CLEAN + "\n"

        # untracked files
        if untracked:
            status += SECTIONS[UNTRACKED_FILES]
            for s, f in untracked:
                status += "\t%s\n" % f.strip()
            status += "\n"

        # unstaged changes
        if unstaged:
            status += SECTIONS[UNSTAGED_CHANGES] if staged else SECTIONS[CHANGES]
            for s, f in unstaged:
                status += "\t%s %s\n" % (STATUS_LABELS[s], f)
            status += "\n"

        # staged changes
        if staged:
            status += SECTIONS[STAGED_CHANGES]
            for s, f in staged:
                status += "\t%s %s\n" % (STATUS_LABELS[s], f)
            status += "\n"

        return status


class GitStatusTextCmd(GitCmd):

    def run(self, edit, *args):
        sublime.error_message("Unimplemented!")

    # status update
    def update_status(self, goto=None):
        self.view.run_command('git_status_refresh', {'goto': goto})

    # selection commands
    def get_first_point(self):
        sels = self.view.sel()
        if sels:
            return sels[0].begin()

    def get_all_points(self):
        sels = self.view.sel()
        return [s.begin() for s in sels]

    # line helpers
    def get_selected_lines(self):
        sels = self.view.sel()
        selected_lines = []
        for selection in sels:
            lines = self.view.lines(selection)
            for line in lines:
                if self.view.score_selector(line.begin(), 'meta.git-status.line') > 0:
                    selected_lines.append(line)
        return selected_lines

    # stash helpers
    def get_all_stash_regions(self):
        return self.view.find_by_selector('meta.git-status.stash.name')

    def get_all_stashes(self):
        stashes = self.get_all_stash_regions()
        return [(self.view.substr(s), self.view.substr(self.view.line(s)).strip()) for s in stashes]

    def get_selected_stashes(self):
        stashes = []
        lines = self.get_selected_lines()

        if lines:
            for s in self.get_all_stash_regions():
                for l in lines:
                    if l.contains(s):
                        name = self.view.substr(s)
                        title = self.view.substr(self.view.line(s)).strip()
                        stashes.append((name, title))
        return stashes

    # file helpers
    def get_all_file_regions(self):
        return self.view.find_by_selector('meta.git-status.file')

    def get_all_files(self):
        files = self.get_all_file_regions()
        return [(self.section_at_region(f), self.view.substr(f)) for f in files]

    def get_selected_file_regions(self):
        files = []
        lines = self.get_selected_lines()

        if not lines:
            return files

        for f in self.get_all_file_regions():
            for l in lines:
                if l.contains(f):
                    # check for renamed
                    linestr = self.view.substr(l).strip()
                    if linestr.startswith(STATUS_LABELS['R']) and ' -> ' in linestr:
                        names = self.view.substr(f)
                        # find position of divider
                        e = names.find(' -> ')
                        s = e + 4
                        # add both files
                        f1 = sublime.Region(f.begin(), f.begin() + e)
                        f2 = sublime.Region(f.begin() + s, f.end())
                        files.append((self.section_at_region(f), f1))
                        files.append((self.section_at_region(f), f2))
                    else:
                        files.append((self.section_at_region(f), f))

        return files

    def get_selected_files(self):
        return [(s, self.view.substr(f)) for s, f in self.get_selected_file_regions()]

    def get_status_lines(self):
        lines = []
        chunks = self.view.find_by_selector('meta.git-status.line')
        for c in chunks:
            lines.extend(self.view.lines(c))
        return lines

    # section helpers
    def get_sections(self):
        sections = self.view.find_by_selector('constant.other.git-status.header')
        return sections

    def section_at_point(self, point):
        for s in list(SECTIONS.keys()):
            if self.view.score_selector(point, SECTION_SELECTOR_PREFIX + s) > 0:
                return s

    def section_at_region(self, region):
        return self.section_at_point(region.begin())

    # goto helpers
    def logical_goto_next_file(self):
        goto = "file:1"
        files = self.get_selected_files()
        if files:
            section, filename = files[-1]
            goto = "file:%s:%s" % (filename, section)
        return goto

    def logical_goto_next_stash(self):
        goto = "stash:1"
        stashes = self.get_selected_stashes()
        if stashes:
            goto = "stash:%s:stashes" % (stashes[-1][0])
        return goto


class GitStatusMoveCmd(GitStatusTextCmd):

    def goto(self, goto):
        what, which, where = self.parse_goto(goto)
        if what == "section":
            self.move_to_section(which, where)
        elif what == "item":
            self.move_to_item(which, where)
        elif what == "file":
            self.move_to_file(which, where)
        elif what == "stash":
            self.move_to_stash(which, where)
        elif what == "point":
            try:
                point = int(which)
                self.move_to_point(point)
            except ValueError:
                pass

    def parse_goto(self, goto):
        what, which, where = None, None, None
        parts = goto.split(':')
        what = parts[0]
        if len(parts) > 1:
            try:
                which = int(parts[1])
            except ValueError:
                which = parts[1]
        if len(parts) > 2:
            try:
                where = int(parts[2])
            except ValueError:
                where = parts[2]
        return (what, which, where)

    def move_to_point(self, point):
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(point))

        #if not self.view.visible_region().contains(point):
        pointrow, _ = self.view.rowcol(point)
        pointstart = self.view.text_point(max(pointrow - 3, 0), 0)
        pointend = self.view.text_point(pointrow + 3, 0)

        pointregion = sublime.Region(pointstart, pointend)

        if pointrow < 10:
            self.view.set_viewport_position((0.0, 0.0), False)
        elif not self.view.visible_region().contains(pointregion):
            self.view.show(pointregion, False)

        #sublime.set_timeout(partial(self.adjust_viewport, point), 0)

    # def adjust_viewport(self, point):
    #     _, view_begin = self.view.viewport_position()
    #     _, view_height = self.view.viewport_extent()
    #     view_end = view_begin + view_height

    #     _, point_begin = self.view.text_to_layout(point)
    #     point_end = point_begin + self.view.line_height()

    #     underflow = max(view_begin - point_begin, 0)
    #     overflow = max(point_end - view_end, 0)

    #     if overflow > 0:
    #         self.view.set_viewport_position((0.0, view_begin + overflow + 5), False)
    #     elif underflow > 0:
    #         self.view.set_viewport_position((0.0, view_begin - underflow - 5), False)

    def move_to_region(self, region):
        self.move_to_point(self.view.line(region).begin())

    def prev_region(self, regions, point):
        before = [r for r in regions if self.view.line(r).end() < point]
        return before[-1] if before else regions[-1]

    def next_region(self, regions, point):
        after = [r for r in regions if self.view.line(r).begin() > point]
        return after[0] if after else regions[0]

    def next_or_prev_region(self, direction, regions, point):
        if direction == "next":
            return self.next_region(regions, point)
        else:
            return self.prev_region(regions, point)

    def move_to_section(self, which, where=None):
        if which in range(1, 5):
            sections = self.get_sections()
            if sections and len(sections) >= which:
                section = sections[which - 1]
                self.move_to_region(section)
        elif which in list(SECTIONS.keys()):
            sections = self.get_sections()
            for section in sections:
                if self.section_at_region(section) == which:
                    self.move_to_region(section)
                    return
        elif which in ('next', 'prev'):
            point = self.get_first_point()
            sections = self.get_sections()
            if point and sections:
                next = self.next_or_prev_region(which, sections, point)
                self.move_to_region(next)

    def move_to_item(self, which=1, where=None):
        if which in ('next', 'prev'):
            point = self.get_first_point()
            regions = self.get_status_lines()
            if point and regions:
                next = self.next_or_prev_region(which, regions, point)
                self.move_to_region(next)

    def move_to_file(self, which=1, where=None):
        if isinstance(which, int):
            files = self.get_all_file_regions()
            if files:
                if len(files) >= which:
                    self.move_to_region(self.view.line(files[which - 1]))
                else:
                    self.move_to_region(self.view.line(files[-1]))
            elif self.get_all_stash_regions():
                self.move_to_stash(1)
            elif self.view.find(GIT_WORKING_DIR_CLEAN, 0, sublime.LITERAL):
                region = self.view.find(GIT_WORKING_DIR_CLEAN, 0, sublime.LITERAL)
                self.move_to_region(region)
        elif which in ('next', 'prev'):
            point = self.get_first_point()
            regions = self.get_all_file_regions()
            if point and regions:
                next = self.next_or_prev_region(which, regions, point)
                self.move_to_region(next)
        elif which and where:
            regions = self.get_all_file_regions()
            section_regions = [r for r in regions if self.section_at_region(r) == where]
            if section_regions:
                prev_regions = [r for r in section_regions if self.view.substr(r) < which]
                next_regions = [r for r in section_regions if self.view.substr(r) >= which]
                if next_regions:
                    next = next_regions[0]
                else:
                    next = prev_regions[-1]
                self.move_to_region(next)
            else:
                sections = set([self.section_at_region(r) for r in regions])
                idx = SECTION_ORDER.index(where)
                while idx > 0:
                    idx -= 1
                    section = SECTION_ORDER[idx]
                    if section in sections:
                        section_regions = [r for r in regions if self.section_at_region(r) == section]
                        self.move_to_region(section_regions[-1])
                        return
                self.move_to_file(1)

    def move_to_stash(self, which, where=None):
        if which is not None and where:
            which = str(which)
            stash_regions = self.get_all_stash_regions()
            if stash_regions:
                prev_regions = [r for r in stash_regions if self.view.substr(r) < which]
                next_regions = [r for r in stash_regions if self.view.substr(r) >= which]
                if next_regions:
                    next = next_regions[0]
                else:
                    next = prev_regions[-1]
                self.move_to_region(next)
            else:
                self.move_to_file(1)
        elif isinstance(which, int):
            stashes = self.get_all_stash_regions()
            if stashes:
                if len(stashes) >= which:
                    self.move_to_region(self.view.line(stashes[which - 1]))
                else:
                    self.move_to_region(self.view.line(stashes[-1]))


class GitStatusCommand(WindowCommand, GitStatusBuilder):
    """
    Documentation coming soon.
    """

    def run(self, refresh_only=False):
        repo = self.get_repo(silent=True if refresh_only else False)
        if not repo:
            return

        title = GIT_STATUS_VIEW_TITLE_PREFIX + os.path.basename(repo)

        view = find_view_by_settings(self.window, git_view='status', git_repo=repo)
        if not view and not refresh_only:
            view = self.window.new_file()

            view.set_name(title)
            view.set_syntax_file(GIT_STATUS_VIEW_SYNTAX)
            view.set_scratch(True)
            view.set_read_only(True)

            view.settings().set('git_view', 'status')
            view.settings().set('git_repo', repo)
            view.settings().set('__vi_external_disable', get_setting('git_status_disable_vintageous') is True)

            for key, val in list(GIT_STATUS_VIEW_SETTINGS.items()):
                view.settings().set(key, val)

        if view is not None:
            self.window.focus_view(view)
            view.run_command('git_status_refresh')


class GitStatusRefreshCommand(TextCommand, GitStatusBuilder, GitStatusMoveCmd):
    _lpop = False

    def is_visible(self):
        return False

    def run(self, edit, goto=None):
        if not self.view.settings().get('git_view') == 'status':
            return

        repo = self.get_repo()
        if not repo:
            return

        status = self.build_status(repo)
        if not status:
            return

        self.view.set_read_only(False)
        self.view.replace(edit, sublime.Region(0, self.view.size()), status)
        self.view.set_read_only(True)

        if goto:
            self.goto(goto)
        else:
            self.goto(GOTO_DEFAULT)


class GitStatusEventListener(EventListener):

    def on_activated(self, view):
        if view.settings().get('git_view') == 'status' and get_setting('git_update_status_on_focus', True):
            goto = None
            if view.sel():
                goto = "point:%s" % view.sel()[0].begin()
            view.run_command('git_status_refresh', {'goto': goto})


class GitStatusBarUpdater(threading.Thread, GitCmd):
    _lpop = False

    def __init__(self, bin, encoding, fallback, repo, kind, view, *args, **kwargs):
        super(GitStatusBarUpdater, self).__init__(*args, **kwargs)
        self.bin = bin
        self.encoding = encoding
        self.fallback = fallback
        self.repo = repo
        self.kind = kind
        self.view = view

    def build_command(self, cmd):
        return self.bin + self.opts + [c for c in cmd if c]

    def run(self):
        branch = self.git_string(['symbolic-ref', '-q', 'HEAD'], cwd=self.repo,
                                 ignore_errors=True, encoding=self.encoding, fallback=self.fallback)
        if not branch:
            return

        branch = branch[11:] if branch.startswith('refs/heads/') else branch

        if self.kind == 'simple':
            msg = "On {branch}".format(branch=branch)
        else:
            self.git_exit_code(['update-index', '--refresh'], cwd=self.repo, encoding=self.encoding, fallback=self.fallback)
            unpushed = self.git_exit_code(['diff', '--exit-code', '--quiet', '@{upstream}..'], cwd=self.repo, encoding=self.encoding, fallback=self.fallback)
            staged = self.git_exit_code(['diff-index', '--quiet', '--cached', 'HEAD'], cwd=self.repo, encoding=self.encoding, fallback=self.fallback)
            unstaged = self.git_exit_code(['diff-index', '--quiet', 'HEAD'], cwd=self.repo, encoding=self.encoding, fallback=self.fallback)
            msg = 'On {branch}{dirty} in {repo}{unpushed}'.format(
                branch=branch,
                dirty='*' if (staged or unstaged) else '',
                repo=os.path.basename(self.repo),
                unpushed=' with unpushed' if unpushed == 1 else ''
            )

        sublime.set_timeout(partial(self.view.set_status, 'git-status', msg), 0)
        # self.view.set_status('git-status', msg)


class GitStatusBarEventListener(EventListener, GitCmd):
    _lpop = False

    def on_activated(self, view):
        if sublime.version() < '3000':
            self.set_status(view)

    def on_load(self, view):
        if sublime.version() < '3000':
            self.set_status(view)

    def on_post_save(self, view):
        if sublime.version() < '3000':
            self.set_status(view)

    def on_activated_async(self, view):
        self.set_status(view)

    def on_load_async(self, view):
        self.set_status(view)

    def on_post_save_async(self, view):
        self.set_status(view)

    def set_status(self, view):
        kind = get_setting('git_status_bar', 'fancy')
        if kind not in ('fancy', 'simple'):
            return

        repo = self.get_repo_from_view(view)
        if not repo:
            return

        bin = get_executable('git', self.bin)
        encoding = get_setting('encoding', 'utf-8')
        fallback = get_setting('fallback_encodings', [])

        updater = GitStatusBarUpdater(bin, encoding, fallback, repo, kind, view)
        updater.start()


class GitQuickStatusCommand(WindowCommand, GitCmd, GitStatusHelper):
    """
    Show an abbreviated status in the quick bar.

    As an alternative to the full status window, a list of changed files is presented
    the quick bar. Next to each filename there is an abbreviation, denoting the files
    status.

    This status contains 2 characters, X and Y. For paths with merge conflicts, X and Y show the
    modification states of each side of the merge. For paths that do not have merge conflicts,
    X shows the status of the index, and Y shows the status of the work tree.

    The statuses are as follows:

    * **' '** = unmodified
    * **M** = modified
    * **A** = added
    * **D** = deleted
    * **R** = renamed
    * **C** = copied
    * **U** = updated but unmerged
    * **?** = untracked

    Selecting an entry in the list will bring up a diff view of the file.
    """

    def run(self):
        repo = self.get_repo()
        if not repo:
            return

        status = self.get_porcelain_status(repo)
        if not status:
            status = [GIT_WORKING_DIR_CLEAN]

        def on_done(idx):
            if idx == -1 or status[idx] == GIT_WORKING_DIR_CLEAN:
                return
            state, filename = status[idx][0:2], status[idx][3:]
            index, worktree = state
            if state == '??':
                return sublime.error_message("Cannot show diff for untracked files.")

            window = self.window
            if worktree != ' ':
                window.run_command('git_diff', {'repo': repo, 'path': filename})
            if index != ' ':
                window.run_command('git_diff', {'repo': repo, 'path': filename, 'cached': True})

        self.window.show_quick_panel(status, on_done, sublime.MONOSPACE_FONT)


class GitStatusMoveCommand(TextCommand, GitStatusMoveCmd):

    def is_visible(self):
        return False

    def run(self, edit, goto="file:1"):
        self.goto(goto)


class GitStatusStageCommand(TextCommand, GitStatusTextCmd):

    def run(self, edit, stage="file"):
        repo = self.get_repo()
        if not repo:
            return

        goto = None
        if stage == "all":
            self.add_all(repo)
        elif stage == "unstaged":
            self.add_all_unstaged(repo)
        elif stage == "section":
            points = self.get_all_points()
            sections = set([self.section_at_point(p) for p in points])
            if UNTRACKED_FILES in sections and UNSTAGED_CHANGES in sections:
                self.add_all(repo)
            elif UNSTAGED_CHANGES in sections:
                self.add_all_unstaged(repo)
            elif UNTRACKED_FILES in sections:
                self.add_all_untracked(repo)
        elif stage == "file":
            files = self.get_selected_files()
            untracked = [f for s, f in files if s in (UNTRACKED_FILES,)]
            unstaged = [f for s, f in files if s in (UNSTAGED_CHANGES,)]
            if untracked:
                self.add(repo, untracked)
            if unstaged:
                self.add_update(repo, unstaged)
            goto = self.logical_goto_next_file()

        self.update_status(goto)

    def add(self, repo, files):
        return self.git(['add', '--'] + files, cwd=repo)

    def add_update(self, repo, files):
        return self.git(['add', '--update', '--'] + files, cwd=repo)

    def add_all(self, repo):
        return self.git(['add', '--all'], cwd=repo)

    def add_all_unstaged(self, repo):
        return self.git(['add', '--update', '.'], cwd=repo)

    def add_all_untracked(self, repo):
        untracked = self.git_lines(['ls-files', '--other', '--exclude-standard'], cwd=repo)
        return self.git(['add', '--'] + untracked, cwd=repo)


class GitStatusUnstageCommand(TextCommand, GitStatusTextCmd):

    def run(self, edit, unstage="file"):
        repo = self.get_repo()
        if not repo:
            return

        goto = None
        if unstage == "all":
            self.unstage_all(repo)
        elif unstage == "file":
            files = self.get_selected_files()
            staged = [f for s, f in files if s == STAGED_CHANGES]
            if staged:
                self.unstage(repo, staged)
                goto = self.logical_goto_next_file()

        self.update_status(goto)

    def no_commits(self, repo):
        return 0 != self.git_exit_code(['rev-list', 'HEAD', '--max-count=1'])

    def unstage(self, repo, files):
        if self.no_commits(repo):
            return self.git(['rm', '--cached', '--'] + files, cwd=repo)
        return self.git(['reset', '-q', 'HEAD', '--'] + files, cwd=repo)

    def unstage_all(self, repo):
        if self.no_commits(repo):
            return self.git(['rm', '-r', '--cached', '.'], cwd=repo)
        return self.git(['reset', '-q', 'HEAD'], cwd=repo)


class GitStatusOpenFileCommand(TextCommand, GitStatusTextCmd):

    def run(self, edit):
        repo = self.view.settings().get('git_repo')
        if not repo:
            return

        transient = get_setting('git_status_open_files_transient', True) is True
        files = self.get_selected_files()
        window = self.view.window()

        for s, f in files:
            filename = os.path.join(repo, f)
            if transient:
                window.open_file(filename, sublime.TRANSIENT)
            else:
                window.open_file(filename)


class GitStatusIgnoreCommand(TextCommand, GitStatusTextCmd):

    IGNORE_TRACKED = (u"The following files have already been added to git. "
                      u"Adding them to .gitignore will not exclude them from being tracked by git. "
                      u"Are you sure you want to continue?")
    IGNORE_CONFIRMATION = u"Are you sure you want add the following patterns to .gitignore?"
    IGNORE_BUTTON = u"Add to .gitignore"
    IGNORE_NO_FILES = u"No files selected for ignore."
    IGNORE_LABEL = "Ignore pattern:"

    def run(self, edit, ask=True, edit_pattern=False):
        window = self.view.window()
        repo = self.get_repo()
        if not repo:
            return

        files = self.get_selected_files()
        to_ignore = [f for _, f in files]

        tracked = [f for s, f in files if s != UNTRACKED_FILES]
        if tracked and not self.confirm_tracked(tracked):
            return

        if not to_ignore:
            sublime.error_message(self.IGNORE_NO_FILES)
            return

        if edit_pattern:
            patterns = []
            to_ignore.reverse()

            def on_done(pattern=None):
                if pattern:
                    patterns.append(pattern)
                if to_ignore:
                    filename = to_ignore.pop()
                    window.show_input_panel(self.IGNORE_LABEL, filename, on_done, noop, on_done)
                elif patterns:
                    if ask:
                        if not self.confirm_ignore(patterns):
                            return

                    self.add_to_gitignore(repo, patterns)
                    goto = self.logical_goto_next_file()
                    self.update_status(goto)

            filename = to_ignore.pop()
            window.show_input_panel(self.IGNORE_LABEL, filename, on_done, noop, on_done)
        else:
            if ask:
                if not self.confirm_ignore(to_ignore):
                    return
            self.add_to_gitignore(repo, to_ignore)
            goto = self.logical_goto_next_file()
            self.update_status(goto)

    def confirm_ignore(self, patterns):
        return self.confirm(self.IGNORE_CONFIRMATION, patterns, self.IGNORE_BUTTON)

    def confirm_tracked(self, patterns):
        return self.confirm(self.IGNORE_TRACKED, patterns, u"Continue")

    def confirm(self, message, patterns, button):
        msg = message
        msg += "\n\n"
        msg += "\n".join(patterns[:10])
        if len(patterns) > 10:
            msg += "\n"
            msg += "(%s more...)" % len(patterns) - 10
        return sublime.ok_cancel_dialog(msg, button)

    def add_to_gitignore(self, repo, patterns):
        gitignore = os.path.join(repo, '.gitignore')
        contents = []

        # read existing gitignore
        if os.path.exists(gitignore):
            with open(gitignore, 'r+') as f:
                contents = [l.strip() for l in f]
        logger.debug('Initial .gitignore: %s', contents)

        # add new patterns to the end
        for p in patterns:
            if p not in contents:
                logger.debug('Adding to .gitignore: %s', p)
                contents.append(p)

        # always add a newline
        contents.append('')

        # write gitignore
        with open(gitignore, 'w+') as f:
            f.write("\n".join(contents))
        logger.debug('Final .gitignore: %s', contents)

        return contents


class GitStatusDiscardCommand(TextCommand, GitStatusTextCmd):

    DELETE_UNTRACKED_CONFIRMATION = "Delete all untracked files and directories?"

    def run(self, edit, discard="item"):
        repo = self.get_repo()
        if not repo:
            return

        goto = None
        if discard == "section":
            points = self.get_all_points()
            sections = set([self.section_at_point(p) for p in points])
            all_files = self.get_all_files()

            if STASHES in sections:
                self.discard_all_stashes(repo)

            if UNTRACKED_FILES in sections:
                self.discard_all_untracked(repo)

            files = [i for i in all_files if i[0] in (UNSTAGED_CHANGES, STAGED_CHANGES)]
            if files:
                self.discard_files(repo, files)

        elif discard == "item":
            files = self.get_selected_files()
            stashes = self.get_selected_stashes()
            if files:
                self.discard_files(repo, files)
            if stashes:
                self.discard_stashes(repo, stashes)
            goto = self.logical_goto_next_file()

        elif discard == "all":
            self.discard_all(repo)

        self.update_status(goto)

    # global discards

    def discard_all_stashes(self, repo):
        if sublime.ok_cancel_dialog('Discard all stashes?', 'Discard'):
            self.git(['stash', 'clear'], cwd=repo)

    def discard_all_untracked(self, repo):
        if sublime.ok_cancel_dialog(self.DELETE_UNTRACKED_CONFIRMATION, 'Delete'):
            self.git(['clean', '-d', '--force'], cwd=repo)

    def discard_all(self, repo):
        if sublime.ok_cancel_dialog("Discard all staged and unstaged changes?", "Discard"):
            if sublime.ok_cancel_dialog("Are you absolutely sure?", "Discard"):
                self.git(['reset', '--hard'], cwd=repo)

    # individual discards

    def discard_stashes(self, repo, stashes):
        # build message
        stashlist = "\n  ".join([t for _, t in stashes])
        msgtemplate = "Are you sure you want to discard the following stashes?\n\n  {stashes}"

        # ask for confirmation
        if sublime.ok_cancel_dialog(msgtemplate.format(stashes=stashlist), 'Discard'):
            nums = reversed(sorted(int(n) for n, _ in stashes))
            for n in nums:
                self.git(['stash', 'drop', '--quiet', 'stash@{%s}' % n], cwd=repo)

    def discard_files(self, repo, files):
        # See if any of the files cannot be discarded
        error = "You can't discard staged changes to the following files. Please unstage them first:\n\n  {errfiles}"
        errlist = []
        for s, f in files:
            if s == STAGED_CHANGES and not self.is_up_to_date(repo, f):
                errlist.append(f)

        if errlist:
            errfiles = "\n  ".join(errlist)
            sublime.error_message(error.format(errfiles=errfiles))
            return

        # Confirm before unstaging any files
        confirm = "Are you sure you want to perform the following actions?\n\n  {actions}"
        actionlist = []
        for s, f in files:
            staged = s == STAGED_CHANGES
            status = self.get_staging_status(repo, f) if staged else self.get_worktree_status(repo, f)

            if staged and f in errlist:
                continue

            if s == UNTRACKED_FILES or status == 'N':
                action = 'Delete: '
            elif status == 'D':
                action = 'Resurrect: '
            else:
                action = 'Discard: '

            actionlist.append("{action} {file}".format(action=action, file=f))

        if not actionlist:
            return

        actions = "\n  ".join(actionlist)
        if not sublime.ok_cancel_dialog(confirm.format(actions=actions), 'Continue'):
            return

        # perform various unstaging/deleting/resurrection actions
        for s, f in files:
            staged = s == STAGED_CHANGES
            status = self.get_staging_status(repo, f) if staged else self.get_worktree_status(repo, f)

            if staged and not self.is_up_to_date(repo, f):
                continue

            if s == UNTRACKED_FILES:
                self.git(['clean', '-d', '--force', '--', f], cwd=repo)
            elif status == 'D':
                self.git(['reset', '-q', '--', f], cwd=repo)
                self.git(['checkout', '--', f], cwd=repo)
            elif status == 'N':
                self.git(['rm', '-f', '--', f], cwd=repo)
            else:
                if staged:
                    self.git(['checkout', 'HEAD', '--', f], cwd=repo)
                else:
                    self.git(['checkout', '--', f], cwd=repo)

    # status helpers

    def is_up_to_date(self, repo, filename):
        return self.git_exit_code(['diff', '--quiet', '--', filename], cwd=repo) == 0

    def get_worktree_status(self, repo, filename):
        output = self.git_string(['diff', '--name-status', '--', filename], cwd=repo)
        if output:
            status, _ = output.split('\t')
            return status

    def get_staging_status(self, repo, filename):
        output = self.git_string(['diff', '--name-status', '--cached', '--', filename], cwd=repo)
        if output:
            status, _ = output.split('\t')
            return status


class GitStatusStashCmd(GitStatusTextCmd, GitStashHelper, GitErrorHelper):

    def pop_or_apply_selected_stashes(self, cmd):
        repo = self.get_repo()
        if not repo:
            return

        goto = None
        stashes = self.get_selected_stashes()
        if stashes:
            for name, title in stashes:
                if sublime.ok_cancel_dialog('Are you sure you want to %s %s?' % (cmd, title), "%s stash" % cmd.capitalize()):
                    exit, stdout, stderr = self.git(['stash', cmd, '-q', 'stash@{%s}' % name], cwd=repo)
                    if exit != 0:
                        sublime.error_message(self.format_error_message(stderr))
            if cmd == "apply":
                region = self.view.line(self.get_first_point())
                goto = "point:%s" % region.begin()
            else:
                goto = self.logical_goto_next_stash()

        self.update_status(goto)


class GitStatusStashApplyCommand(TextCommand, GitStatusStashCmd):

    def run(self, edit):
        self.pop_or_apply_selected_stashes('apply')


class GitStatusStashPopCommand(TextCommand, GitStatusStashCmd):

    def run(self, edit):
        self.pop_or_apply_selected_stashes('pop')


class GitStatusDiffCommand(TextCommand, GitStatusTextCmd):

    def run(self, edit):
        repo = self.get_repo()
        if not repo:
            return

        files = self.get_selected_files()
        window = self.view.window()

        for s, f in files:
            if s != UNTRACKED_FILES:
                cached = (s == STAGED_CHANGES)
                window.run_command('git_diff', {'repo': repo, 'path': f, 'cached': cached})
