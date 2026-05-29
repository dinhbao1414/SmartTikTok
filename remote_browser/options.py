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

import json
import os

def args_default():
    return [
        '--disable-background-networking',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-breakpad',
        '--disable-browser-side-navigation',
        '--disable-client-side-phishing-detection',
        '--disable-crash-reporter',
        '--disable-default-apps',
        '--disable-dev-shm-usage',
        # '--disable-extensions',
        '--disable-features=NetworkService,NetworkServiceInProcess,PreloadMediaEngagementData,AutofillServerCommunication,PasswordLeakDetection,site-per-process',
        '--site-per-process',
        '--disable-hang-monitor',
        '--disable-logging',
        '--disable-notifications',
        '--disable-popup-blocking',
        '--disable-prompt-on-repost',
        '--disable-sync',
        '--disable-translate',
        '--lang=en-US',
        '--metrics-recording-only',
        '--no-default-browser-check',
        '--no-first-run',
        '--no-service-autorun',
        '--password-store=basic',
        '--safebrowsing-disable-auto-update',
        '--use-mock-keychain'
    ]

def prefs_default():
    return {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "webrtc.ip_handling_policy": "disable_non_proxied_udp",
        "webrtc.multiple_routes_enabled": False,
        # "translate_enabled": False,
        # "translate": {"enabled": "false"},
        "webrtc.nonproxied_udp_enabled": False,
    }

class BrowserOptions:
    def __init__(self):
        self.arguments = args_default()
        self.preferences = prefs_default()
        self.__binary_location = None
        self.__debugger_address = None


    @staticmethod
    def _undot_key(key, value):
        """turn a (dotted key, value) into a proper nested dict"""
        if "." in key:
            key, rest = key.split(".", 1)
            value = BrowserOptions._undot_key(rest, value)
        return {key: value}

    @staticmethod
    def _merge_nested(a, b):
        """
        merges b into a
        leaf values in a are overwritten with values from b
        """
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    BrowserOptions._merge_nested(a[key], b[key])
                    continue
            a[key] = b[key]
        return a
    
    def add_argument(self, argument):
        if argument not in self.arguments:
            self.arguments.append(argument)
            
    def add_preference(self, key, value):
        if not isinstance(key, str):
            raise TypeError("Preference key must be a string")
        self.preferences[key] = value


    def to_command_args(self):
        return " ".join(list(dict.fromkeys(self.arguments)))
    
    def save_preferences(self, profile_path=None):
        try:
            if not profile_path and 'user-data-dir' not in self.to_command_args():
                raise ValueError("Profile path must be provided or 'user-data-dir' must be set in command args.")
            if not profile_path:
                for arg in self.arguments:
                    if arg.startswith('--user-data-dir="'):
                        profile_path = arg.split('="', 1)[1].split('"')[0]
                        break
            preferences_path = os.path.join(profile_path, "Default", "Preferences")
            dir_profile = os.path.dirname(preferences_path)
            os.makedirs(dir_profile, exist_ok=True)
            
            if os.path.exists(preferences_path):
                with open(preferences_path, 'r', encoding='utf-8') as f:
                    prefs = json.load(f)
            else:
                prefs = {}
            
            prefs.update(self.preferences)
            
            undot_prefs = {}
            for key, value in prefs.items():
                undot_prefs = self._merge_nested(
                    undot_prefs, self._undot_key(key, value)
                )

            if os.path.exists(preferences_path):
                with open(preferences_path, encoding="latin1", mode="r") as f:
                    undot_prefs = self._merge_nested(json.load(f), undot_prefs)

            with open(preferences_path, encoding="latin1", mode="w") as f:
                json.dump(undot_prefs, f)
            
            del self.preferences
                
        except ValueError as e:
            raise ValueError(f"Invalid input: {e}")
        except OSError as e:
            raise IOError(f"Failed to create or write preferences file: {e}")
        except Exception as e:
            raise IOError(f"An unexpected error occurred while saving preferences: {e}")

    @property
    def binary_location(self):
        return self.__binary_location
    
    @binary_location.setter
    def binary_location(self, executable_path: str):
        if not isinstance(executable_path, str):
            raise TypeError("Binary location must be a string")
        if not os.path.exists(executable_path):
            raise FileNotFoundError(f"Binary location not found: {executable_path}")
        self.__binary_location = executable_path
    
    @property
    def debugger_address(self):
        return self.__debugger_address
    
    @debugger_address.setter
    def debugger_address(self, debugger_address: str):
        self.__debugger_address = debugger_address