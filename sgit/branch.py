# coding: utf-8
#import re

#import sublime
#from sublime_plugin import WindowCommand

#from .util import noop
from .cmd import GitCmd
from .helpers import GitBranchHelper


class GitBranchWindowCmd(GitCmd, GitBranchHelper):
    pass
