#####################################################################################
##   _______ _       _____  ____  ______ _________          __     _____  ______   ##
##  |__   __| |     / ____|/ __ \|  ____|__   __\ \        / /\   |  __ \|  ____|  ##
##     | |  | |    | (___ | |  | | |__     | |   \ \  /\  / /  \  | |__) | |__     ##
##     | |  | |     \___ \| |  | |  __|    | |    \ \/  \/ / /\ \ |  _  /|  __|    ##
##     | |  | |____ ____) | |__| | |       | |     \  /\  / ____ \| | \ \| |____   ##
##     |_|  |______|_____/ \____/|_|       |_|      \/  \/_/    \_\_|  \_\______|  ##
##                                                                                 ##
#####################################################################################

## Remote Browser Module BUIDER BY LTT Dev - TLSOFTWARE - ZALO: 0358768395

################## CONTACT ###################
##      __AUTHOR__    : LTT Dev             ##
##      __TELEGRAM__  : @ltts_dev           ##
##      __ZALO__      : 0358768395          ##
##      __FACEBOOK__  : TaiLe.TLSoftware    ##
##############################################

import os
import re

__all__ = [
    'browser_map', 
    'find_version_from_path',
    'find_browser_executable'
]
browser_map = {
    'Chrome': {
        'sub_path': 'Google/Chrome/Application',
        'name_exe': 'chrome.exe'
    },
    'Cốc Cốc': {
        'sub_path': 'CocCoc/Browser/Application',
        'name_exe': 'browser.exe'
    },
    'Brave': {
        'sub_path': 'BraveSoftware/Brave-Browser/Application',
        'name_exe': 'brave.exe'
    },
    'Chromium': {
        'sub_path': './Browser/chrome-win',
        'name_exe': 'chrome.exe'
    },
    'Edge': {
        'sub_path': 'Microsoft/Edge/Application',
        'name_exe': 'msedge.exe'
    }
}

def find_version_from_path(path_browser: str):
    try:
        for i in os.listdir('\\'.join(os.path.abspath(path_browser).split('\\')[0:-1])):
            list_split = re.search(r"(\d+)", i)
            if list_split: 
                return int(list_split.group())
    except: 
        pass

def find_browser_executable(name_browser):
    candidates = set()
    for item in map(
        os.environ.get,
        ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA", "PROGRAMW6432"),
    ):
        if item is not None:
            for subitem in (
                browser_map[name_browser]['sub_path'],
            ):
                candidates.add(os.sep.join((item, subitem, browser_map[name_browser]['name_exe'])))

    for candidate in candidates:
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return os.path.normpath(candidate)
    
    return None