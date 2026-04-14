"""
Centralized path resolution for both development and PyInstaller-bundled modes.

When bundled as .exe:
  - Bundled resources (templates, static, .env) live in sys._MEIPASS (temp dir)
  - Writable files (data/current_state.json) live next to the .exe
When running as normal Python:
  - Everything lives in the script's directory
"""

import os
import sys


def _is_frozen():
    return getattr(sys, "frozen", False)


def bundle_path():
    """Path to bundled read-only resources (templates, static, .env)."""
    if _is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def app_path():
    """Path to the directory where the .exe lives (writable data goes here)."""
    if _is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def data_dir():
    """Writable data directory."""
    return os.path.join(app_path(), "data")


def data_file():
    """Path to current_state.json (writable)."""
    return os.path.join(data_dir(), "current_state.json")


def env_file():
    """Path to .env file (bundled with the app)."""
    return os.path.join(bundle_path(), ".env")
