#####################################################################################
##   _______ _       _____  ____  ______ _________          __     _____  ______   ##
##  |__   __| |     / ____|/ __ \|  ____|__   __\ \        / /\   |  __ \|  ____|  ##
##     | |  | |    | (___ | |  | | |__     | |   \ \  /\  / /  \  | |__) | |__     ##
##     | |  | |     \___ \| |  | |  __|    | |    \ \/  \/ / /\ \ |  _  /|  __|    ##
##     | |  | |____ ____) | |__| | |       | |     \  /\  / ____ \| | \ \| |____   ##
##     |_|  |______|_____/ \____/|_|       |_|      \/  \/_/    \_\_|  \_\______|  ##
##                                                                                 ##
#####################################################################################

## CDPWebdriver BUIDER BY LTT Dev - TLSOFTWARE - ZALO: 0358768395

################## CONTACT ###################
##      __AUTHOR__    : LTT Dev             ##
##      __TELEGRAM__  : @ltts_dev           ##
##      __ZALO__      : 0358768395          ##
##      __FACEBOOK__  : TaiLe.TLSoftware    ##
##############################################

from typing import Union, List

from .webelement import WebElement
from ..exceptions import NoSuchElementException
from ..type.browser_support import By

class Select:
    def __init__(self, webelement: WebElement):
        if not webelement:
            raise NoSuchElementException("Select.__init__ using WebElement not NoneType")
        self._element = webelement
        self.__target__ = webelement.__target__
        self._options = self.get_options()
    
    def get_options(self) -> Union[WebElement, List[WebElement]]:
        return self._element.find_elements(By.TAG_NAME, 'option')
    
    def select_value(self, value: str):
        for option in self._options:
            if option.get_att("value") == value:
                option.set_att("selected", "true")
                break
    
    def select_index(self, index: int):
        option = self._options[index]
        option.set_att('selected', 'true')
