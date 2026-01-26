"""Custom errors for the invoice synchronizer domain."""


class ConfigError(Exception):
    """Error raised when there are configuration issues."""
    pass


class AuthenticationError(Exception):
    """Error raised when authentication fails."""
    pass


class FetchDataError(Exception):
    """Error raised when fetching data from external sources fails."""
    pass


class UploadError(Exception):
    """Error raised when uploading data to external sources fails."""
    pass


class UpdateError(Exception):
    """Error raised when updating data fails."""
    pass


class ParseDataError(Exception):
    """Error raised when parsing data fails."""
    pass