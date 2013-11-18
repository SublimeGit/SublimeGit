SublimeGit Issues
=================

This is a public repository for hosting the Issue Tracker. Please see if the issue you're about to report is already on the roadmap. Of course, if you have anything to add, feel free to create the issue anyway.

This is pretty much a dump of my internal todo-list, and as such it doesn't contain references to all of the issues. It's more about my thoughts on where SublimeGit is headed. So just because an issue isn't on this list doesn't mean it's not being worked on.

I generally try to release at least one new feature as well as a couple of bugfixes in each release. Release frequency varies, but I try my best to release a minor feature every 1-3 weeks.


Roadmap
-------

**1.0.X (Minor releases)**

Prioritized features (These are what's being worked on, in this order):
 - Interactive rebase. (Issue #54, #9)
 - Pushing and pulling of tags. (Issue #68)
 - Add unmerged paths to status view.

Various features (In no particular order):
 - Difftool command. (Issue #43)
 - Open status view after select/init repo when running `Git: Status`.
 - Force reindex of project-wide tags on checkout.
 - Open file at correct point with <enter> in diff view.
 - `Git: Commit & Push` command.
 - `Git-flow: Feature Publish` command. (Issue #28)
 - `Git-flow: Feature Pull` command.
 - Open `Git: Remote > Show`
 - Browse forwards and backwards in `Git: Show`. (Related to issue #72)
 - `Git: Show` syntax highlighting (Related to issue #72)
 - Cherry-picking.
 - Improved syntax highlighting for `Git: Blame`.
 - Alternative short syntax for `Git: Blame`.

Bugs (In no particular order):
 - Handle username/password/passphrase freezes better.
 - Fix some whitespace problems.
 - Improve reload logic to get rid of need to restart Sublime Text after some updates.
 - Improve status view cursor location logic. (Issue #10)
 - Commit message is empty on merge commits.
 - Git-flow issues. (Issue #63, #51)

**1.1.0**

Planned Features:
 - `Git: Log` view. (See below)
 - `Git: Branch` view. (See below)
 - Add unpushed commits to status view.
 - Hub integration. (Issue #30)

**1.2.0 and later**
 - `Git: Annotate`.
 - git-svn integration. (Issue #37)
 - Squashing.
 - Bisecting.


Feature Descriptions
--------------------

**Git: Log View** (Issue #70)

Show a pretty tree (ala glog alias). Make sure the branches are colored in the correct way, if possible (use the ascii color codes and make a custom colorscheme for the view).

It should be possible to walk through the graph using n and p, and maybe jumping to merges and branches in an intelligent way. Pressing enter should open a commit in the commit view, and show a color-coded diff. Pressing space should append the commit to an already existing commit view and scroll the view.

It should also be possible to refresh the log by pressing r. In the bottom of the view there should be a text which allows for loading X more lines (if necessary).


**Git: Branch View**

List of local and remote branches, with meta-information for each one, as well as easy navigation.

should allow
 - pushing
 - pulling
 - fetching
 - rebasing
 - publishing
 - unpublishing
 - checkout
 - delete
 - merge
 - rebase
 - rename
 - etc.
