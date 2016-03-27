

Customizations
==============

The defaults of SublimeGit are not for everyone. Here is a list of common customizations which you might or might not be right for you.

.. _customizations-commands:

Custom Commands
---------------
By using the Git: Custom Command action in SublimeGit, you can create your own SublimeGit aliases. If you have a command that you run often, you can save it with an alias and get access to it in the Sublime Text quick bar.

To do this, we need to first cover how to set up custom commands in Sublime Text. Inside your packages directory (Go to ``Preferences > Browse Packages``) there will be a directory called ``User``. Inside this directory, you can place files with the extension ``.sublime-commands`` and they will be picked up by Sublime Text. In the following we're only going to present a short example of how to use the **Git: Custom Command** to extend SublimeGit, but there are more fun things that can be done. For an overview of the format of these files, see the `Sublime Text Docs on Command Files <http://docs.sublimetext.info/en/latest/reference/command_palette.html>`_.

Now, create a file in the ``User`` directory and name it ``Git.sublime-commands``. Add this to it::

    [
        {
            "caption": "Git: Graph Log",
            "command": "git_custom",
            "args": {
                "cmd": "log --graph --oneline",
                "output": "panel",
                "async": false
            }
        },
        {
            "caption": "Git: Diff Master",
            "command": "git_custom",
            "args": {
                "cmd": "diff master",
                "output": "view",
                "async": true,
                "syntax": "Packages/SublimeGit/syntax/SublimeGit Diff.tmLanguage"
            }
        }
    ]

This tells Sublime Text that you want a command named "Git: Graph Log", and when it is executed, Sublime Text should run the command ``git_custom`` from SublimeGit, which should in turn execute ``git log --graph --oneline`` synchronously and present the output to you in a new panel. Same goes for the "Git: Diff Master" command, except the command will be asynchronous, the output will be in a view, and the view will have the specified syntax file.

As you can see, the custom commands can take different arguments. Please see :ref:`custom-commands` for possible values of these arguments.


Keyboard Shortcuts
------------------
For information on keybindings in general, please see the `Sublime Text Docs <http://docs.sublimetext.info/en/latest/customization/key_bindings.html>`_.


Run a Command (e.g. Git: Status)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you want to figure out what a command is called, you can set Sublime Text to log all commands by executing the following snippet in the console::

    sublime.log_commands(True)

After you've done that, all commands will then be logged to the console. Using this, you can see that the **Git: Status** command is called ``git_status``.

With this information, you can add something like this to your keymap, to open git status when pressing ``ctrl+alt+g``::

    { "keys": ["ctrl+alt+g"], "command": "git_status"}

.. note::
    You can turn off the command logging again with::

        sublime.log_commands(False)


Add a Key Binding to a Command in the Status View
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Let's say you want to have `t` add a tag from the status view. Naturally you don't want this shortcut to be available everywhere (that would make it quite hard to write anything). The solution for this is specifying that the shortcut should only be available in the status view, like so::

    { "keys": ["t"], "command": "git_add_tag",
        "context": [{ "key": "selector", "operator": "equal", "operand": "text.git-status" }]
    }


Jump to a Specific Section in the Status View
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
It is possible to jump to a specific section in the git status view, with a set of shortcuts like this::

    // Section shortcuts
    { "keys": ["ctrl+1"], "command": "git_status_move", "args": {"goto": "section:stashes"},
        "context": [
            { "key": "selector", "operator": "equal", "operand": "text.git-status" }
        ]
    },
    { "keys": ["ctrl+2"], "command": "git_status_move", "args": {"goto": "section:untracked_files"},
        "context": [
            { "key": "selector", "operator": "equal", "operand": "text.git-status" }
        ]
    },
    { "keys": ["ctrl+3"], "command": "git_status_move", "args": {"goto": "section:unstaged_changes"},
        "context": [
            { "key": "selector", "operator": "equal", "operand": "text.git-status" }
        ]
    },
    { "keys": ["ctrl+4"], "command": "git_status_move", "args": {"goto": "section:staged_changes"},
        "context": [
            { "key": "selector", "operator": "equal", "operand": "text.git-status" }
        ]
    },
    { "keys": ["ctrl+5"], "command": "git_status_move", "args": {"goto": "section:unpushed_commits"},
        "context": [
            { "key": "selector", "operator": "equal", "operand": "text.git-status" }
        ]
    }

.. warning::
    These shortcuts will overwrite the "focus group" shortcuts built into Sublime Text.


Color Scheme
------------
SublimeGit uses a lot of different colors. Though great care has been taken in picking the SublimeGit colors to generally look good in the default Sublime Text themes, you might want to customize them.


Setting a Different Color Scheme
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you want to use a different color scheme for some SublimeGit view altogether, you can do this by going to ``Preferences > Settings > More > Syntax Specific - User`` while having a SublimeGit view open (i.e. the status or commit view), and then adding a color scheme setting for the given syntax like so::

    "color_scheme": "Packages/Color Scheme - Default/Monokai.tmTheme"


Customizing Individual Colors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A full detailing of creating a color scheme is outside the scope of this documentation. A quick googling on ``sublime text color schemes`` or ``textmate color schemes`` should bring up plenty of resources.

To find out which scope you will need to colorize, put the cursor on the text in question, and press ``ctrl+shift+p``. This will show the scope under the cursor in the status bar.
