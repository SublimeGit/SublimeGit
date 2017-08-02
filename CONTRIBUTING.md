Contributing to SublimeGit
=======================

This is the summary for contributing code, documentation, testing, and filing
issues. Please read it carefully to help making the code review process go as
smoothly as possible and maximize the likelihood of your contribution being
merged.

How to contribute
-----------------

The preferred workflow for contributing to SublimeGit is to fork the
[main repository](https://github.com/SublimeGit/SublimeGit) on
GitHub, clone, and develop on a branch. Steps:

1. Fork the [project repository](https://github.com/SublimeGit/SublimeGit)
   by clicking on the 'Fork' button near the top right of the page. This creates
   a copy of the code under your GitHub user account. For more details on
   how to fork a repository see [this guide](https://help.github.com/articles/fork-a-repo/).

2. Clone your fork of the SublimeGit repo from your GitHub account to your local disk:

   ```bash
   $ git clone git@github.com:YourLogin/SublimeGit.git
   $ cd SublimeGit
   ```

3. Create a ``feature`` branch to hold your development changes:

   ```bash
   $ git checkout -b my-feature
   ```

   Always use a ``feature`` branch. It's good practice to never work on the ``master`` branch!

4. Develop the feature on your feature branch. Add changed files using ``git add`` and then ``git commit`` files:

   ```bash
   $ git add modified_files
   $ git commit
   ```

   to record your changes in Git, then push the changes to your GitHub account with:

   ```bash
   $ git push -u origin my-feature
   ```

5. Follow [these instructions](https://help.github.com/articles/creating-a-pull-request-from-a-fork)
to create a pull request from your fork. This will send an email to the committers.

(If any of the above seems like magic to you, please look up the
[Git documentation](https://git-scm.com/documentation) on the web, or ask a friend or another contributor for help.)

Pull Request Checklist
----------------------

We recommend that your contribution complies with the following rules before you
submit a pull request:

-  If your pull request addresses an issue, please use the pull request title to
   describe the issue and mention the issue number in the pull request
   description. This will make sure a link back to the original issue is
   created. Use "closes #PR-NUM" or "fixes #PR-NUM" to indicate github to
   automatically close the related issue. Use any other keyword (i.e: works on,
   related) to avoid github to close the referenced issue.

You can also check for common programming errors with the following
tools:

-  No pyflakes warnings, check with:

  ```bash
  $ pip install pyflakes
  $ pyflakes path/to/module.py
  ```

-  No PEP8 warnings, check with:

  ```bash
  $ pip install pep8
  $ pep8 path/to/module.py
  ```

-  AutoPEP8 can help you fix some of the easy redundant errors:

  ```bash
  $ pip install autopep8
  $ autopep8 path/to/pep8.py
  ```

Filing bugs
-----------
We use Github issues to track all bugs and feature requests; feel free to
open an issue if you have found a bug or wish to see a feature implemented.

It is recommended to check that your issue complies with the
following rules before submitting:

-  Verify that your issue is not being currently addressed by other
   [issues](https://github.com/SublimeGit/SublimeGit/issues?q=)
   or [pull requests](https://github.com/SublimeGit/SublimeGit/pulls?q=).

-  Please ensure all code snippets and error messages are formatted in
   appropriate code blocks.
   See [Creating and highlighting code blocks](https://help.github.com/articles/creating-and-highlighting-code-blocks).
