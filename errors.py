class WakeError(Exception):
    """Raised when an error occurs while trying to wake the host"""
    pass

class ConnectionError(Exception):
    """Raised when the application can't connect to the host"""
    pass

class CommandError(Exception):
    """Raised when the application can't send a command to the host"""
    pass

class AuthError(Exception):
    """Authentication could not complete properly"""
    pass