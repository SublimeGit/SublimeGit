# coding: utf-8
import sys
import logging

import sublime

# set up some logging
settings = sublime.load_settings('SublimeGit.sublime-settings')

loglevel = getattr(logging, settings.get('log_level', '').upper(), logging.WARNING)
logging.basicConfig(level=loglevel,
    format="[%(asctime)s - %(levelname)s - %(name)s] %(message)s")

logger = logging.getLogger('sgit')

# reload modules if necessary
LOAD_ORDER = [
    # base
    'sgit',
    'sgit.util',
    'sgit.cmd',
    'sgit.helpers',

    # commands
    'sgit.help',
    'sgit.cli',
    'sgit.repo',
    'sgit.diff',
    'sgit.show',
    'sgit.log',
    'sgit.stash',
    'sgit.branch',
    'sgit.remote',
    'sgit.status',
    'sgit.add',
    'sgit.commit',
    'sgit.checkout',
    'sgit.merge',

    # extensions
    'sgit.legit',
    'sgit.git_flow'
]

needs_reload = [n for n, m in sys.modules.items() if n[0:4] == 'sgit' and m != None]

reloaded = []
for module in LOAD_ORDER:
    if module in needs_reload:
        reloaded.append(module)
        reload(sys.modules[module])
if reloaded:
    logger.debug('Reloaded %s' % ", ".join(reloaded))


# import commands and listeners
from sgit import DebugReloader

from sgit.util import GitPanelWriteCommand, GitPanelAppendCommand

#from sgit.cli import GitCliCommand, GitCliAsyncCommand

from sgit.repo import GitInitCommand, GitSwitchRepoCommand

from sgit.diff import GitDiffCommand, GitDiffRefreshCommand

from sgit.show import GitShowCommand, GitShowRefreshCommand

from sgit.help import GitHelpCommand, GitVersionCommand

from sgit.log import GitLogCommand, GitQuickLogCommand, GitQuickLogCurrentFileCommand

from sgit.remote import (GitPushCurrentBranchCommand, GitPullCurrentBranchCommand,
    GitPushPullAllCommand, GitFetchCommand, GitRemoteCommand, GitRemoteAddCommand)

from sgit.status import (GitStatusCommand, GitStatusRefreshCommand, GitQuickStatusCommand,
    GitStatusMoveCommand, GitStatusStageCommand,
    GitStatusUnstageCommand, GitStatusDiscardCommand,
    GitStatusOpenFileCommand, GitStatusDiffCommand, GitStatusIgnoreCommand,
    GitStatusStashCmd, GitStatusStashApplyCommand, GitStatusStashPopCommand)
from sgit.status import GitStatusBarEventListener, GitStatusEventListener

from sgit.add import GitQuickAddCommand, GitAddCurrentFileCommand

from sgit.commit import (GitCommitCommand, GitCommitTemplateCommand,
    GitCommitPerformCommand, GitQuickCommitCommand)
from sgit.commit import GitCommitEventListener

from sgit.stash import (GitStashCommand, GitSnapshotCommand,
    GitStashApplyCommand, GitStashPopCommand)

from sgit.checkout import (GitCheckoutBranchCommand, GitCheckoutCommitCommand,
    GitCheckoutNewBranchCommand)

from sgit.merge import GitMergeCommand

# import legit if enabled
if settings.get('git_extensions', {}).get('legit', True):
    from sgit.legit import (LegitSwitchCommand, LegitSyncCommand, LegitPublishCommand,
        LegitUnpublishCommand, LegitHarvestCommand, LegitSproutCommand, LegitGraftCommand,
        LegitBranchesCommand)


# shut down logging
def unload_handler():
    logging.shutdown()
