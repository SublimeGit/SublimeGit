Troubleshooting
===============

SublimeGit Can't Find Git
-------------------------

Please see :ref:`config-git-path`


.. _remote-issues:

Nothing Happens When Pushing, Pulling or Fetching From a Remote
---------------------------------------------------------------

Please see :ref:`prereq-git-remote`. Below you will find solutions submitted by SublimeGit users:


Solution by Albert Santini (`Issue #3 <https://github.com/SublimeGit/SublimeGit/issues/3>`_)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
I configured the git bash shell on windows 7 following GitHub help to start a ssh agent, because I don't want to type every time the passphrase for my ssh key.

I added to that configuration, in .bashrc, the following lines::

    setx SSH_AUTH_SOCK $SSH_AUTH_SOCK 1> nul
    setx SSH_AGENT_PID $SSH_AGENT_PID 1> nul

These lines add the environment variables to windows user profile.

So the git executable, configured in SublimeGit, can read the variables and use the correct protocol.

Firstly I start the bash shell and then I start SublimeText editor.

Now SublimeGit works perfectly.


Solution by Henry Mei (`Issue #15 <https://github.com/SublimeGit/SublimeGit/issues/15>`_)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
I am outlining my workaround and hope this will be beneficial for anyone working with Windows.

It seems that SublimeGit requires credential storing for the command prompt (i.e. cmd.exe) and not Git Bash. I will assume that we're using msysgit. Make sure Git is added to your PATH.

1. Grab a copy of PuTTY, Plink, Pageant, and PuTTYgen from here and save them somewhere (e.g. I just threw them all in C:\PuTTY\).
2. Add a system variable called GIT_SSH that points to the location of Plink (e.g. C:\PuTTY\plink.exe). If you're using an older version of mysysgit, there was actually an option to use Plink instead of OpenSSH.
3. Generate your public/private key pair using PuTTYgen. Be sure to secure your key by using a passphrase. You should be generating a SSH-2 RSA key of typically 1024 bits. Save the private key somewhere, and add the public key generated to the list of SSH public keys on your GitHub account (i.e. go to github.com and look in your account settings).
4. Grab GitHub's public key. Use PuTTY to SSH into github.com. If you've never done this before, it should pop up an alert saying that the server's host key is not cached in the registry. Hit "Yes" to add the key to PuTTY's cache. After doing this, exit PuTTY. We won't be using it again.
5. Run Pageant. This will create an icon in your system tray. Double click to open a window where you can add your private key. The agent will sit in the background, much like ssh-agent, and provide authentication when necessary.

.. note::
    If you tried the OpenSSH workaround detailed `here <https://help.github.com/articles/working-with-ssh-key-passphrases>`_, you can just convert your OpenSSH private key to a PuTTY key also using PuTTYgen (the public key will be same regardless). Your OpenSSH keys will be in ~.ssh, which is %USERPROFILE%\.ssh . OpenSSH public keys have the \*.pub extension and private keys no extension. PuTTY private keys have the \*.ppk extensions. Make sure to choose the OpenSSH private key when opening with PuTTYgen and save it as a \*.ppk.

As long as Pageant is running, any git calls through the command prompt should be automatically authenticated, allowing SublimeGit to not freeze.

Pageant will default to a clean session every time it runs, but it takes key paths as parameters (i.e. pageant.exe ... ). There are a few ways to make things easier. You can add the path to the keys after the target path in the Pageant shortcut (i.e. for me, this would be "C:\PuTTY\pageant.exe" %USERPROFILE%\.ssh\id_rsa.ppk ) or just write a batch file to make it autostart in Windows. Pageant will always prompt for the passphrases of keys you auto-load on startup.


Solution by Mario Basic (`Issue #59 <https://github.com/SublimeGit/SublimeGit/issues/59>`_)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are on Windows and when you try to push or pull using this plugin nothing happens or it pushes forever, You have to add a system variable to your SSH keys.

 - Right-click on Computer
 - Choose Properties
 - Click on Advanced System Settings
 - Click on Environment Variables
 - In the bottom section (System Variables) Click on New
 - For Variable name type: ``HOME``
 - For Variable path type: ``C:\Users\your-user-folder\``
 - Click OK


The Output From Git Commands Look Weird (ANSI Escape Codes)
-----------------------------------------------------------

This happens if you have any of the ``color.*`` git options set to ``true`` (or ``always``). SublimeGit tries to remove the colors on everything, but sometimes one slip through. If you see one in the wild, please report it at support@sublimegit.net.

To make sure that you don't get the escape codes in SublimeGit, but still get pretty colors when using git from the terminal, we recommend setting the ``color.*`` config values to ``auto`` like so::

    git config --global color.ui auto
    git config --global color.branch auto
    git config --global color.diff auto
    git config --global color.status auto

After which the relevant part of your ``.gitconfig`` will look something like this:

.. code-block:: ini

    [color]
        diff = auto
        status = auto
        branch = auto
        ui = auto
