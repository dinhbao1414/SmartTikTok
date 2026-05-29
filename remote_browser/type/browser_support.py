class By:
    ID = "id"
    XPATH = "xpath"
    NAME = "name"
    TAG_NAME = "tag name"
    CLASS_NAME = "class name"
    CSS_SELECTOR = "css selector"


class Type:
    ENTER = {"key": "Enter", "code": "Enter", "location": 0}
    SHIFT = {"key": "Shift", "code": "ShiftLeft", "location": 1}
    RIGHT_SHIFT = {"key": "Shift", "code": "ShiftRight", "location": 2}
    CTRL = {"key": "Control", "code": "ControlLeft", "location": 1}
    RIGHT_CTRL = {"key": "Control", "code": "ControlRight", "location": 2}
    ALT = {"key": "Alt", "code": "AltLeft", "location": 1}
    RIGHT_ALT = {"key": "Alt", "code": "AltRight", "location": 2}
    BACKSPACE = {"key": "Backspace", "code": "Backspace", "location": 0}
    TAB = {"key": "Tab", "code": "Tab", "location": 0}
    ESCAPE = {"key": "Escape", "code": "Escape", "location": 0}
    ARROW_UP = {"key": "ArrowUp", "code": "ArrowUp", "location": 0}
    ARROW_DOWN = {"key": "ArrowDown", "code": "ArrowDown", "location": 0}
    ARROW_LEFT = {"key": "ArrowLeft", "code": "ArrowLeft", "location": 0}
    ARROW_RIGHT = {"key": "ArrowRight", "code": "ArrowRight", "location": 0}
    DELETE = {"key": "Delete", "code": "Delete", "location": 0}
