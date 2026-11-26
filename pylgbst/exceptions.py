"""
Errors raised to callers of hub operations, shared by the sync and async APIs
"""


class HubError(Exception):
    pass


class HubDisconnected(HubError, ConnectionError):
    """The link to the hub is gone: lost, closed, or the hub switched off"""


class ReplyTimeout(HubError, TimeoutError):
    """The hub did not respond to a request in time"""


class CommandFailed(HubError, RuntimeError):
    """
    The hub reported an error for a command.
    Subclasses RuntimeError, which the library raised for these before.
    """

    def __init__(self, message, command=None, error_code=None):
        super().__init__(message)
        self.command = command
        self.error_code = error_code


class CommandDiscarded(CommandFailed):
    """The port dropped an output command: it was rejected, or another command took over the port"""
