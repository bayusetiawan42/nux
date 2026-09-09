# core/errors.py
# Error hierarchy for Nux.


class NuxError(Exception):
    pass


class NoAPIKeyError(NuxError):
    pass


class AllKeysRateLimitedError(NuxError):
    pass


class AuthenticationFailedError(NuxError):
    pass


class APIRequestError(NuxError):
    pass
