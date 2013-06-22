# coding: utf-8
import sys
import logging

import sublime

# set up some logging
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s - %(levelname)s - %(name)s] %(message)s")
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

    # meta
    'sgit.sublimegit',

    # extensions
    'sgit.git_extensions.legit',
    'sgit.git_extensions.git_flow',
]

needs_reload = [n for n, m in list(sys.modules.items()) if n[0:4] == 'sgit' and m is not None]

reloaded = []
for module in LOAD_ORDER:
    if module in needs_reload:
        reloaded.append(module)
        reload(sys.modules[module])
if reloaded:
    logger.debug('Reloaded %s' % ", ".join(reloaded))


# import commands and listeners
if sys.version_info[0] == 2:
    settings = sublime.load_settings('SublimeGit.sublime-settings')
    ext = settings.get('git_extensions', {})

    # set log level
    lvl = getattr(logging, settings.get('log_level', '').upper(), logging.WARNING)
    logger.setLevel(lvl)

    from sgit import *
    from sgit.git_extensions.legit import *
    from sgit.git_extensions.git_flow import *

    # Enable plugins
    git_extensions.legit.enabled = ext.get('legit', True)
    git_extensions.git_flow.enabled = ext.get('git_flow', True)

    def unload_handler():
        logging.shutdown()
else:
    from .sgit import *
    from .sgit.plugins.legit import *
    from .sgit.plugins.git_flow import *

    def plugin_loaded():
        settings = sublime.load_settings('SublimeGit.sublime-settings')
        ext = settings.get('git_extensions', {})

        # set log level
        lvl = getattr(logging, settings.get('log_level', '').upper(), logging.WARNING)
        logger.setLevel(lvl)

        # Enable plugins
        plugins.legit.enabled = ext.get('legit', True)
        plugins.git_flow.enabled = ext.get('git_flow', True)

    def plugin_unloaded():
        logging.shutdown()
