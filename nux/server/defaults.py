# server/defaults.py
# Portable defaults for the daemon. Override these for custom deployments.

import os

from nux.core.constants import NUX_DIR

SOCKET_PATH = os.path.join(NUX_DIR, "server.sock")
PID_FILE = os.path.join(NUX_DIR, "server.pid")
STARTUP_WAIT = 8.0
