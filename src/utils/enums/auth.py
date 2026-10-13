from enum import Enum

class AuthEnums(Enum):
    INVALID_ACESS_TOKEN = "Invalid access token"
    INVALID_OR_EXPIRED_ACESS_TOKEN = "Invalid or expired access token"
    USER_NOT_FOUND = "User not found"