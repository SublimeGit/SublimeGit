# coding: utf-8
import os
import sys
import logging

import sublime

# set up some logging
#settings = sublime.load_settings('SublimeGit.sublime-settings')

#loglevel = getattr(logging, settings.get('log_level', '').upper(), logging.WARNING)
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s - %(levelname)s - %(name)s] %(message)s",
    filename=os.path.join(os.path.dirname(__file__), 'sgit.log')
)


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
    'sgit.plugins.legit',
    'sgit.plugins.git_flow',
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
    from sgit import *
else:
    from .sgit import *


# import legit if enabled
# if settings.get('git_extensions', {}).get('legit', True):
#     from sgit.plugins.legit import (LegitSwitchCommand, LegitSyncCommand, LegitPublishCommand,
#                                     LegitUnpublishCommand, LegitHarvestCommand, LegitSproutCommand,
#                                     LegitGraftCommand, LegitBranchesCommand)


# # import git-flow if enabled
# if settings.get('git_extensions', {}).get('git_flow', True):
#     from sgit.plugins.git_flow import (GitFlowInitCommand,
#                                        GitFlowFeatureCommand, GitFlowFeatureStartCommand, GitFlowFeatureFinishCommand,
#                                        GitFlowReleaseCommand, GitFlowReleaseStartCommand, GitFlowReleaseFinishCommand,
#                                        GitFlowHotfixStartCommand, GitFlowHotfixFinishCommand)


# shut down logging
def unload_handler():
    logging.shutdown()
