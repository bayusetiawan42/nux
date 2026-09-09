# Nux - Your terminal on steroids.

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nux")
except PackageNotFoundError:
    __version__ = "0.1.0"
