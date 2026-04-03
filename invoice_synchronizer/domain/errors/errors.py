"""Custom errors for the invoice synchronizer domain."""


class ConfigError(Exception):
    """Error raised when there are configuration issues."""


class AuthenticationError(Exception):
    """Error raised when authentication fails."""


class FetchDataError(Exception):
    """Error raised when fetching data from external sources fails."""


class UploadError(Exception):
    """Error raised when uploading data to external sources fails."""


class UpdateError(Exception):
    """Error raised when updating data fails."""


class ParseDataError(Exception):
    """Error raised when parsing data fails."""
