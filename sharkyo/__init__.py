# Sharkyo - Your shark in the terminal.

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sharkyo")
except PackageNotFoundError:
    __version__ = "0.1.0"
