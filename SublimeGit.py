# coding: utf-8
import sys
import logging

import sublime

# set up some logging
logging.basicConfig(level=logging.WARNING, format="[%(asctime)s - %(levelname)-8s - %(name)s] %(message)s")
logger = logging.getLogger('SublimeGit')

# reload modules if necessary
LOAD_ORDER = [
    # base
    '',
    '.util',
    '.cmd',
    '.helpers',

    # commands
    '.help',
    '.cli',
    '.repo',
    '.diff',
    '.show',
    '.blame',
    '.log',
    '.stash',
    '.branch',
    '.remote',
    '.status',
    '.add',
    '.commit',
    '.checkout',
    '.merge',

    # meta
    '.sublimegit',

    # extensions
    '.git_extensions.legit',
    '.git_extensions.git_flow',
]

needs_reload = [n for n, m in list(sys.modules.items()) if n[0:4] == 'sgit' and m is not None]

reloaded = []
for prefix in ('sgit', 'sgit2', 'sgit3'):
    for postfix in LOAD_ORDER:
        module = prefix + postfix
        if module in needs_reload:
            reloaded.append(module)
            reload(sys.modules[module])
if reloaded:
    logger.info('Reloaded %s' % ", ".join(reloaded))


# import commands and listeners
if sys.version_info[0] == 2:
    settings = sublime.load_settings('SublimeGit.sublime-settings')
    ext = settings.get('git_extensions', {})

    # set log level
    lvl = getattr(logging, settings.get('log_level', '').upper(), logging.WARNING)
    logger.setLevel(lvl)

    try:
        from sgit2 import *
        from sgit2.git_extensions.legit import *
        from sgit2.git_extensions.git_flow import *
    except ImportError as e:
        try:
            from sgit import *
            from sgit.git_extensions.legit import *
            from sgit.git_extensions.git_flow import *
        except ImportError:
            raise

    # Enable plugins
    git_extensions.legit.enabled = ext.get('legit', True)
    git_extensions.git_flow.enabled = ext.get('git_flow', True)

    def unload_handler():
        logging.shutdown()
else:
    try:
        from .sgit3 import *
        from .sgit3.git_extensions.legit import *
        from .sgit3.git_extensions.git_flow import *
    except ImportError as e:
        try:
            from .sgit import *
            from .sgit.git_extensions.legit import *
            from .sgit.git_extensions.git_flow import *
        except ImportError:
            raise

    def plugin_loaded():
        settings = sublime.load_settings('SublimeGit.sublime-settings')
        ext = settings.get('git_extensions', {})

        # set log level
        lvl = getattr(logging, settings.get('log_level', '').upper(), logging.WARNING)
        logger.setLevel(lvl)

        # Enable plugins
        git_extensions.legit.enabled = ext.get('legit', True)
        git_extensions.git_flow.enabled = ext.get('git_flow', True)

    def plugin_unloaded():
        logging.shutdown()
