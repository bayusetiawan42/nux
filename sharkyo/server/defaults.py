# server/defaults.py
# Portable defaults for the daemon. Override these for custom deployments.

import os

DEFAULT_SHARKYO_DIR = os.path.expanduser("~/.sharkyo")
SOCKET_PATH = os.path.join(DEFAULT_SHARKYO_DIR, "server.sock")
PID_FILE = os.path.join(DEFAULT_SHARKYO_DIR, "server.pid")
STARTUP_WAIT = 8.0
