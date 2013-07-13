# coding: utf-8

__version__ = '1.0.12'


# Import all the commands

from .util import GitPanelWriteCommand, GitPanelAppendCommand

#from .cli import GitCliCommand, GitCliAsyncCommand

from .repo import GitInitCommand, GitSwitchRepoCommand

from .diff import GitDiffCommand, GitDiffRefreshCommand

from .show import GitShowCommand, GitShowRefreshCommand

from .help import GitHelpCommand, GitVersionCommand

from .log import GitQuickLogCommand, GitQuickLogCurrentFileCommand

from .blame import (GitBlameCommand, GitBlameRefreshCommand, GitBlameShowCommand,
                    GitBlameBlameCommand)
from .blame import GitBlameEventListener

from .remote import (GitPushCurrentBranchCommand, GitPullCurrentBranchCommand,
                     GitPushPullAllCommand, GitFetchCommand, GitPullCommand, GitPushCommand,
                     GitRemoteCommand, GitRemoteAddCommand)

from .status import (GitStatusCommand, GitStatusRefreshCommand, GitQuickStatusCommand,
                     GitStatusMoveCommand, GitStatusStageCommand,
                     GitStatusUnstageCommand, GitStatusDiscardCommand,
                     GitStatusOpenFileCommand, GitStatusDiffCommand,
                     GitStatusIgnoreCommand, GitStatusStashCmd, GitStatusStashApplyCommand,
                     GitStatusStashPopCommand)
from .status import GitStatusBarEventListener, GitStatusEventListener

from .add import GitQuickAddCommand, GitAddCurrentFileCommand

from .commit import (GitCommitCommand, GitCommitTemplateCommand,
                     GitCommitPerformCommand, GitQuickCommitCommand, GitQuickCommitCurrentFileCommand)
from .commit import GitCommitEventListener

from .stash import (GitStashCommand, GitSnapshotCommand,
                    GitStashApplyCommand, GitStashPopCommand)

from .checkout import (GitCheckoutBranchCommand, GitCheckoutCommitCommand,
                       GitCheckoutNewBranchCommand, GitCheckoutCurrentFileCommand)

from .merge import GitMergeCommand

from .sublimegit import (SublimeGitInstallLicenseCommand, SublimeGitBuyLicenseCommand,
                         SublimeGitDocumentationCommand, SublimeGitVersionCommand)


# import plugins

from . import git_extensions
