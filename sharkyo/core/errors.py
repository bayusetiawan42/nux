# core/errors.py
# Error hierarchy for Sharkyo.


class SharkyoError(Exception):
    pass


class NoAPIKeyError(SharkyoError):
    pass


class AllKeysRateLimitedError(SharkyoError):
    pass


class AuthenticationFailedError(SharkyoError):
    pass


class APIRequestError(SharkyoError):
    pass
