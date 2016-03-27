Commands Reference
==================

Creating and Switching Repositories
-----------------------------------
.. _cmd-git-init:
.. autowindowcmd:: sgit.repo.GitInitCommand
.. autowindowcmd:: sgit.repo.GitSwitchRepoCommand


Status
------
.. _cmd-git-status:
.. autowindowcmd:: sgit.status.GitStatusCommand
.. autowindowcmd:: sgit.status.GitQuickStatusCommand

Diffs
-----
.. autowindowcmd:: sgit.diff.GitDiffCommand
.. autowindowcmd:: sgit.diff.GitDiffCachedCommand

Blame
-----
.. autowindowcmd:: sgit.blame.GitBlameCommand

.. _cmd-adding-files:

Adding files
------------
.. autowindowcmd:: sgit.add.GitQuickAddCommand
.. autowindowcmd:: sgit.add.GitAddCurrentFileCommand


Checking out files
------------------
.. autowindowcmd:: sgit.checkout.GitCheckoutCurrentFileCommand


Committing
----------
.. autowindowcmd:: sgit.commit.GitQuickCommitCommand
.. autowindowcmd:: sgit.commit.GitQuickCommitCurrentFileCommand
.. autowindowcmd:: sgit.commit.GitCommitCommand
.. autowindowcmd:: sgit.commit.GitCommitAmendCommand


Logs
----
.. autowindowcmd:: sgit.log.GitLogCommand
.. autowindowcmd:: sgit.log.GitQuickLogCommand
.. autowindowcmd:: sgit.log.GitQuickLogCurrentFileCommand
.. autowindowcmd:: sgit.show.GitShowCommand

.. _branching-merging:

Branching and Merging
---------------------
.. autowindowcmd:: sgit.checkout.GitCheckoutBranchCommand
.. autowindowcmd:: sgit.checkout.GitCheckoutCommitCommand
.. autowindowcmd:: sgit.checkout.GitCheckoutNewBranchCommand
.. autowindowcmd:: sgit.merge.GitMergeCommand


Working with Remotes
--------------------
.. _cmd-add-remote:
.. autowindowcmd:: sgit.remote.GitRemoteAddCommand
.. _cmd-remote:
.. autowindowcmd:: sgit.remote.GitRemoteCommand


Fetching and Pulling
--------------------
.. autowindowcmd:: sgit.remote.GitFetchCommand
.. _cmd-pull:
.. autowindowcmd:: sgit.remote.GitPullCommand
.. autowindowcmd:: sgit.remote.GitPullCurrentBranchCommand


Pushing
-------
.. _cmd-push:
.. autowindowcmd:: sgit.remote.GitPushCommand
.. _cmd-push-current-branch:
.. autowindowcmd:: sgit.remote.GitPushCurrentBranchCommand

.. _stashing:

Stashing
--------
.. autowindowcmd:: sgit.stash.GitStashCommand
.. autowindowcmd:: sgit.stash.GitStashPopCommand
.. autowindowcmd:: sgit.stash.GitStashApplyCommand
.. autowindowcmd:: sgit.stash.GitSnapshotCommand

Tags
----
.. autowindowcmd:: sgit.tag.GitTagCommand
.. autowindowcmd:: sgit.tag.GitAddTagCommand

.. _custom-commands:

Custom Commands
---------------
.. autowindowcmd:: sgit.custom.GitCustomCommand

Browsing Documentation
----------------------
.. _cmd-help:
.. autowindowcmd:: sgit.help.GitHelpCommand
.. autowindowcmd:: sgit.help.GitVersionCommand

SublimeGit
----------
.. autowindowcmd:: sgit.sublimegit.SublimeGitVersionCommand
.. autowindowcmd:: sgit.sublimegit.SublimeGitDocumentationCommand

Gitk
----
.. autowindowcmd:: sgit.gitk.GitGitkCommand
