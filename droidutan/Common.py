#!/usr/bin/python

keyEvents = ['KEYCODE_UNKNOWN', 'KEYCODE_MENU', 'KEYCODE_SOFT_RIGHT', 'KEYCODE_HOME', 'KEYCODE_BACK', 'KEYCODE_CALL', 'KEYCODE_ENDCALL', 'KEYCODE_0', 'KEYCODE_1', 'KEYCODE_2', 'KEYCODE_3', 'KEYCODE_4', 'KEYCODE_5', 'KEYCODE_6', 'KEYCODE_7', 'KEYCODE_8', 'KEYCODE_9', 'KEYCODE_STAR', 'KEYCODE_POUND', 'KEYCODE_DPAD_UP', 'KEYCODE_DPAD_DOWN', 'KEYCODE_DPAD_LEFT', 'KEYCODE_DPAD_RIGHT', 'KEYCODE_DPAD_CENTER', 'KEYCODE_VOLUME_UP', 'KEYCODE_VOLUME_DOWN', 'KEYCODE_POWER', 'KEYCODE_CAMERA', 'KEYCODE_CLEAR', 'KEYCODE_A', 'KEYCODE_B', 'KEYCODE_C', 'KEYCODE_D', 'KEYCODE_E', 'KEYCODE_F', 'KEYCODE_G', 'KEYCODE_H', 'KEYCODE_I', 'KEYCODE_J', 'KEYCODE_K', 'KEYCODE_L', 'KEYCODE_M', 'KEYCODE_N', 'KEYCODE_O', 'KEYCODE_P', 'KEYCODE_Q', 'KEYCODE_R', 'KEYCODE_S', 'KEYCODE_T', 'KEYCODE_U', 'KEYCODE_V', 'KEYCODE_W', 'KEYCODE_X', 'KEYCODE_Y', 'KEYCODE_Z', 'KEYCODE_COMMA', 'KEYCODE_PERIOD', 'KEYCODE_ALT_LEFT', 'KEYCODE_ALT_RIGHT', 'KEYCODE_SHIFT_LEFT', 'KEYCODE_SHIFT_RIGHT', 'KEYCODE_TAB', 'KEYCODE_SPACE', 'KEYCODE_SYM', 'KEYCODE_EXPLORER', 'KEYCODE_ENVELOPE', 'KEYCODE_ENTER', 'KEYCODE_DEL', 'KEYCODE_GRAVE', 'KEYCODE_MINUS', 'KEYCODE_EQUALS', 'KEYCODE_LEFT_BRACKET', 'KEYCODE_RIGHT_BRACKET', 'KEYCODE_BACKSLASH', 'KEYCODE_SEMICOLON', 'KEYCODE_APOSTROPHE', 'KEYCODE_SLASH', 'KEYCODE_AT', 'KEYCODE_NUM', 'KEYCODE_HEADSETHOOK', 'KEYCODE_FOCUS', 'KEYCODE_PLUS', 'KEYCODE_MENU', 'KEYCODE_NOTIFICATION', 'KEYCODE_SEARCH', 'TAG_LAST_KEYCODE']

# Excluding keycodes that would lead out of the app e.g. KEYCODE_POWER or KEYCODE_HOME
selectedKeyEvents = ['KEYCODE_SOFT_RIGHT', 'KEYCODE_BACK', 'KEYCODE_0', 'KEYCODE_1', 'KEYCODE_2', 'KEYCODE_3', 'KEYCODE_4', 'KEYCODE_5', 'KEYCODE_6', 'KEYCODE_7', 'KEYCODE_8', 'KEYCODE_9', 'KEYCODE_STAR', 'KEYCODE_POUND', 'KEYCODE_DPAD_UP', 'KEYCODE_DPAD_DOWN', 'KEYCODE_DPAD_LEFT', 'KEYCODE_DPAD_RIGHT', 'KEYCODE_DPAD_CENTER', 'KEYCODE_VOLUME_UP', 'KEYCODE_VOLUME_DOWN', 'KEYCODE_CLEAR', 'KEYCODE_A', 'KEYCODE_B', 'KEYCODE_C', 'KEYCODE_D', 'KEYCODE_E', 'KEYCODE_F', 'KEYCODE_G', 'KEYCODE_H', 'KEYCODE_I', 'KEYCODE_J', 'KEYCODE_K', 'KEYCODE_L', 'KEYCODE_M', 'KEYCODE_N', 'KEYCODE_O', 'KEYCODE_P', 'KEYCODE_Q', 'KEYCODE_R', 'KEYCODE_S', 'KEYCODE_T', 'KEYCODE_U', 'KEYCODE_V', 'KEYCODE_W', 'KEYCODE_X', 'KEYCODE_Y', 'KEYCODE_Z', 'KEYCODE_COMMA', 'KEYCODE_PERIOD', 'KEYCODE_ALT_LEFT', 'KEYCODE_ALT_RIGHT', 'KEYCODE_SHIFT_LEFT', 'KEYCODE_SHIFT_RIGHT', 'KEYCODE_TAB', 'KEYCODE_SPACE', 'KEYCODE_SYM', 'KEYCODE_EXPLORER', 'KEYCODE_ENVELOPE', 'KEYCODE_ENTER', 'KEYCODE_DEL', 'KEYCODE_GRAVE', 'KEYCODE_MINUS', 'KEYCODE_EQUALS', 'KEYCODE_LEFT_BRACKET', 'KEYCODE_RIGHT_BRACKET', 'KEYCODE_BACKSLASH', 'KEYCODE_SEMICOLON', 'KEYCODE_APOSTROPHE', 'KEYCODE_SLASH', 'KEYCODE_AT', 'KEYCODE_NUM', 'KEYCODE_HEADSETHOOK', 'KEYCODE_FOCUS', 'KEYCODE_PLUS', 'TAG_LAST_KEYCODE']

supportedUIElements = ["CheckBox", "EditText", "RadioButton", "RatingBar", "Switch", "ToggleButton", "Button"]

class Event(object):
    """ A base class for events """
    def __init__(self, eId, eType):
        self.eId = eId
        self.eType = eType
 
    def __str__(self):
        return "{\"id\": \"%s\", \"type\": \"%s\"}" % (self.eId, self.eType)

class PressEvent(Event):
    """ A class for pressing events """
    def __init__(self, eId, eType, eKey):
        super(PressEvent, self).__init__(eId, eType)
        self.eKey = eKey
 
    def __str__(self):
        return "{\"id\": \"%s\", \"type\": \"%s\", \"key\": \"%s\"}" % (self.eId, self.eType, self.eKey)

class GUIEvent(Event):
    """ A class for UI events """
    def __init__(self, eId, eType, eX, eY):
        super(GUIEvent, self).__init__(eId, eType)
        self.eX = eX
        self.eY = eY
    def __str__(self):
        return "{\"id\": \"%s\", \"type\": \"%s\", \"x\": \"%s\", \"y\": \"%s\"}" % (self.eId, self.eType, self.eX, self.eY)

class TextEvent(GUIEvent):
    """ A class for TextViews """
    def __init__(self, eId, eType, eX, eY, eText):
        super(TextEvent, self).__init__(eId, eType, eX, eY)
        self.eText = eText

    def __str__(self):
        return "{\"id\": \"%s\", \"type\": \"%s\", \"x\": \"%s\", \"y\": \"%s\", \"text\": \"%s\"}" % (self.eId, self.eType, self.X, self.Y, self.eText)

class SwipeEvent(GUIEvent):
    """ A class for swiping events """
    def __init__(self, eId, eType, eX, eY, eXd, eYd):
        super(SwipeEvent, self).__init__(eId, eType, eX, eY)
        self.eXd = eXd
        self.eYd = eYd
   
    def __str__(self):
        return "{\"id\": \"%s\", \"type\": \"%s\", \"x\": \"%s\", \"y\": \"%s\", \"xd\": \"%s\", \"yd\": \"%s\"}" % (self.eId, self.eType, self.eX, self.eY, self.eXd, self.eYd)

class BroadcastEvent(Event):
    """ A class for brodcasting intents """
    def __init__(self, eId, eType, eIntent):
        super(BroadcastEvent, self).__init__(eId, eType)
        self.eIntent = eIntent

    def __str__(self):
        return "{\"id\": \"%s\", \"type\": \"%s\", \"intent\": \"%s\"}" % (self.eId, self.eType, self.eIntent)

