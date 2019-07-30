#!/usr/bin/env python

"""
Copyright (c) 2018-2019 cloudmare developer
"""

from __future__ import absolute_import

import codecs
import os
import random
import re
import string
import sys


from lib.parse.colors import white, green, red, yellow, end, info, que, bad, good, run
from pip._internal import main as pipmain

# version (<major>.<minor>.<month>.<day>)
VERSION = "1.6.7.29"
DESCRIPTION = "Automatic CloudProxy and reverse proxy bypass tool"
ISSUES_PAGE = "https://github.com/MrH0wl/Cloudmare/issues/new"
GIT_REPOSITORY = "https://github.com/MrH0wl/Cloudmare.git"
GIT_PAGE = "https://github.com/MrH0wl/Cloudmare"
ZIPBALL_PAGE = "https://github.com/MrH0wl/Cloudmare/zipball/master"
YEAR = '2019'
NAME = 'Cloudmare '
COPYRIGHT = "Copyright %s - GPL v3.0"%(YEAR)

# colorful banner
def logotype():
	print (yellow + '''
  ____ _                 _ __  __
 / ___| | ___  _   _  __| |  \/  | __ _ _ __ ___
| |   | |/ _ \| | | |/ _` | |\/| |/ _` | '__/ _ \\
| |___| | (_) | |_| | (_| | |  | | (_| | | |  __/
 \____|_|\___/ \__,_|\__,_|_|  |_|\__,_|_|  \___| '''+ white + '[' + red + VERSION + white + ']' +'''
''' + green + DESCRIPTION + green + "\n##################################################"+ white + '\n')

# osclear shortcut
def osclear(logotype, unknown):
    isOs = sys.platform.lower()
    if isOs == 'win32':
        os.system('cls')
    elif isOs == 'linux':
        os.system('clear')
    else:
      print(unknown)
      sys.exit()
    print (logotype)

# question shortcut
def quest(question, doY, doN):
    end = ''
    try:
        isPy = sys.version_info[0]
        if isPy == 3:
            question = input(question)
        else:
            question = raw_input(question)
        if question == 'yes' or question == 'y':
            try: 
                exec(doY)
            except KeyboardInterrupt:
                sys.exit()
        elif question == 'no' or question == 'n':
            exec(doN)
        else:
            sys.exit()
        if end == None:
            pass
        else:
            print(end)
        
    except KeyboardInterrupt:
        sys.exit()