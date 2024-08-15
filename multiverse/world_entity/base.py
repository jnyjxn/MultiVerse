from enum import Enum


class WorldEntityActionResult(Enum):
    SUCCESS = 0
    NOOP = 1
    FAIL__INVALID_PASSWORD = 2
    FAIL__NOT_RECOGNISED = 3


class WorldEntityNotFound(Exception):
    """Raised when a WorldEntity name is not recognised from the current list of world entities"""
