"""Project paths and environment loading.

DAVIAM used to build paths with Windows backslashes and read ``.env`` from
the process working directory. Resolving everything from this file means
``python DAVIAM/Main.py`` works from the repository root on Linux and Windows.
"""

import os

from dotenv import dotenv_values

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "Data")
FRONTEND_DIR = os.path.join(ROOT, "Frontend")
FILES_DIR = os.path.join(FRONTEND_DIR, "Files")
GRAPHICS_DIR = os.path.join(FRONTEND_DIR, "Graphics")
BACKEND_DIR = os.path.join(ROOT, "Backend")
ENV_FILE = os.path.join(ROOT, ".env")


def data_path(*parts):
    return os.path.join(DATA_DIR, *parts)


def files_path(*parts):
    return os.path.join(FILES_DIR, *parts)


def graphics_path(*parts):
    return os.path.join(GRAPHICS_DIR, *parts)


def backend_path(*parts):
    return os.path.join(BACKEND_DIR, *parts)


def load_env():
    if os.path.exists(ENV_FILE):
        return dotenv_values(ENV_FILE)
    return {}


def env_get(name, default=None):
    """Return a ``.env`` value, then a process environment value, then ``default``."""
    value = load_env().get(name)
    if value is None or str(value).strip() == "":
        value = os.environ.get(name, default)
    if value is None or str(value).strip() == "":
        return default
    return value


def ensure_runtime_dirs():
    """Create runtime folders and seed status files when they are missing."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FILES_DIR, exist_ok=True)
    defaults = {
        files_path("Mic.data"): "False",
        files_path("Status.data"): "Available ... ",
        files_path("Responses.data"): "",
        files_path("Database.data"): "",
        files_path("ImageGeneration.data"): "False,False",
    }
    for path, content in defaults.items():
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
    chat_log = data_path("ChatLog.json")
    if not os.path.exists(chat_log):
        with open(chat_log, "w", encoding="utf-8") as handle:
            handle.write("[]")
