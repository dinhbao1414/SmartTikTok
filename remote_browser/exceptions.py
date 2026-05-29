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

class ExecutableNotFound(Exception):...
class BrowserError(Exception):...
class NoSuchElementException(Exception):...
class CDPException(Exception):
    def __init__(self, error):
        self.code = error["code"]
        self.message = error["message"]
        super().__init__(error)

class JSEvalException(Exception):
    def __init__(self, exception_details):
        super().__init__()
        self.exc_id = exception_details['exceptionId']
        self.text = exception_details["text"]
        self.line_n = exception_details['lineNumber']
        self.column_n = exception_details['columnNumber']
        exc = exception_details["exception"]
        self.type = exc["type"]
        self.subtype = exc["subtype"]
        self.class_name = exc["className"]
        self.description = exc["description"]
        self.obj_id = exc["objectId"]

    def __str__(self):
        return self.description

class TypeKeyException(Exception):...
class SwitchWindowError(Exception):...
class TargetError(Exception):...
class RemoteException(Exception):...