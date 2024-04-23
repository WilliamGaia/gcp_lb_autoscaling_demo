from enum import Enum, auto

class EventListenerStatus(Enum):
    SCALEOUT_ONLY = auto()
    SCALEIN_ONLY = auto()
    DISABLE_ALL = auto()
    ENABLE_ALL = auto()

class SnoozeTarget(Enum):
    SCALE_IN = auto()
    SCALE_OUT = auto()
    ALL = auto()