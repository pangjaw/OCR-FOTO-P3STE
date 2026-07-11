"""Start Hermes dashboard server from source."""
import os
import sys

HERMES_SRC = r'C:\Users\dikarm\AppData\Local\hermes\hermes-agent'

os.environ.setdefault('HERMES_WEB_DIST',
    os.path.join(HERMES_SRC, 'hermes_cli', 'web_dist'))

sys.path.insert(0, HERMES_SRC)

# web_server imports reference cfg_get etc from hermes_cli
os.chdir(HERMES_SRC)

from hermes_cli.web_server import start_server
start_server(host='127.0.0.1', port=9120, open_browser=False)
