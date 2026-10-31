import asyncio
import datetime
import os
import re
import shutil
import subprocess
import sys
import webbrowser
from urllib.parse import quote_plus

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from rich import print
except ImportError:
    pass

import requests

from llm import groq_chat
from paths import data_path, env_get

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

WEBSITES = {
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "whatsapp": "https://web.whatsapp.com",
    "telegram": "https://web.telegram.org",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://www.netflix.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "discord": "https://discord.com/app",
}

COMMANDS = {
    "chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
    "google chrome": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"],
    "chromium": ["chromium", "chromium-browser"],
    "firefox": ["firefox"],
    "edge": ["microsoft-edge", "microsoft-edge-stable"],
    "notepad": ["gedit", "gnome-text-editor", "kate", "mousepad", "notepad"],
    "calculator": ["gnome-calculator", "kcalc", "calc"],
    "terminal": ["gnome-terminal", "konsole", "x-terminal-emulator"],
    "files": ["nautilus", "dolphin", "thunar"],
    "file explorer": ["explorer", "nautilus", "dolphin"],
    "vscode": ["code"],
    "vs code": ["code"],
    "visual studio code": ["code"],
}

performed = []


def dry_run():
    return os.environ.get("DAVIAM_DRY_RUN") == "1"


def record(kind, detail):
    performed.append((kind, detail))
    if dry_run():
        print(f"[dry-run] {kind}: {detail}")


def GoogleSearch(Topic):
    record("google search", Topic)
    if dry_run():
        return True
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(Topic)}")
    return True


def _content_system():
    username = env_get("Username", "User")
    return [{
        "role": "system",
        "content": (
            f"Hello, I am {username}, you're a content writer. You have to write content "
            "like letters, codes, applications, essays, notes, songs, poems, etc."
        ),
    }]


def _safe_filename(topic):
    cleaned = re.sub(r"[^a-z0-9]+", "", topic.lower())
    return cleaned or "content"


def _open_document(path):
    if sys.platform.startswith("win"):
        subprocess.Popen(["notepad.exe", path])
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-t", path])
        return
    opener = shutil.which("xdg-open")
    if opener:
        subprocess.Popen([opener, path])
        return
    print(f"Wrote content to {path}")


def Content(Topic):
    topic = re.sub(r"(?i)^content\s+", "", Topic).strip()
    record("content", topic)
    if dry_run():
        return True

    history = []

    def ContentWriterAI(prompt):
        history.append({"role": "user", "content": prompt})
        answer = groq_chat(_content_system() + history, max_tokens=2048)
        history.append({"role": "assistant", "content": answer})
        return answer

    content = ContentWriterAI(topic)
    path = data_path(f"{_safe_filename(topic)}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    _open_document(path)
    return True


def YouTubeSearch(Topic):
    record("youtube search", Topic)
    if dry_run():
        return True
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(Topic)}")
    return True


def PlayYoutube(query):
    record("play", query)
    if dry_run():
        return True
    search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    try:
        response = requests.get(search_url, headers={"User-Agent": USER_AGENT}, timeout=10)
        match = re.search(r"watch\?v=[\w-]{11}", response.text)
        if match:
            webbrowser.open("https://www.youtube.com/" + match.group(0))
            return True
    except Exception as error:
        print(f"YouTube lookup failed: {error}")
    webbrowser.open(search_url)
    return True


def _open_known_website(app):
    key = app.strip().lower()
    if key.startswith("http://") or key.startswith("https://"):
        webbrowser.open(key)
        return True
    url = WEBSITES.get(key)
    if url:
        webbrowser.open(url)
        return True
    compact = key.replace(" ", "")
    if compact in WEBSITES:
        webbrowser.open(WEBSITES[compact])
        return True
    return False


def _open_local_command(app):
    key = app.strip().lower()
    candidates = COMMANDS.get(key, [key])
    for candidate in candidates:
        executable = shutil.which(candidate)
        if executable:
            subprocess.Popen([executable])
            return True
    return False


def OpenApp(app, sess=None):
    app = (app or "").strip()
    record("open", app)
    if dry_run() or not app:
        return True

    if sys.platform.startswith("win"):
        try:
            from AppOpener import open as appopen

            appopen(app, match_closest=True, output=True, throw_error=True)
            return True
        except Exception as error:
            print(f"AppOpener could not open {app}: {error}")

    if _open_known_website(app):
        return True
    if _open_local_command(app):
        return True
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(app)}")
    return True


def CloseApp(app):
    app = (app or "").strip()
    record("close", app)
    if dry_run():
        return True
    if "chrome" in app.lower():
        return False

    if sys.platform.startswith("win"):
        try:
            from AppOpener import close

            close(app, match_closest=True, output=True, throw_error=True)
            return True
        except Exception:
            return False

    token = app.split()[0] if app else ""
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", token):
        return False
    try:
        completed = subprocess.run(["pkill", "-x", token], check=False)
        return completed.returncode == 0
    except Exception:
        return False


def _run_volume(action):
    linux_commands = {
        "mute": ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
        "unmute": ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
        "volume up": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"],
        "volume down": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"],
    }
    if sys.platform.startswith("linux") and shutil.which("pactl"):
        try:
            subprocess.run(linux_commands[action], check=False, timeout=5)
            return True
        except Exception as error:
            print(f"Could not change volume with pactl: {error}")

    key_name = {
        "mute": "volume mute",
        "unmute": "volume mute",
        "volume up": "volume up",
        "volume down": "volume down",
    }[action]
    try:
        import keyboard

        keyboard.press_and_release(key_name)
        return True
    except Exception as error:
        print(f"Could not send the {key_name} key: {error}")
        return False


def System(command):
    command = (command or "").lower().strip()
    record("system", command)
    if dry_run():
        return True
    if "unmute" in command:
        action = "unmute"
    elif "mute" in command:
        action = "mute"
    elif "volume up" in command or "increase" in command or "turn up" in command:
        action = "volume up"
    elif "volume down" in command or "decrease" in command or "turn down" in command:
        action = "volume down"
    else:
        print(f"No system command matched: {command}")
        return False
    return _run_volume(action)


def Reminder(details):
    details = (details or "").strip()
    record("reminder", details)
    if dry_run():
        return True
    path = data_path("Reminders.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {details}\n")
    print(f"Reminder saved to {path}")
    return True


async def TranslateAndExecute(commands: list[str]):
    funcs = []

    for command in commands:
        if command.startswith("open "):
            target = command.removeprefix("open ").strip()
            if target.lower() in {"it", "file"}:
                continue
            funcs.append(asyncio.to_thread(OpenApp, target))

        elif command.startswith("general ") or command.startswith("realtime "):
            continue

        elif command.startswith("close "):
            funcs.append(asyncio.to_thread(CloseApp, command.removeprefix("close ").strip()))

        elif command.startswith("play "):
            funcs.append(asyncio.to_thread(PlayYoutube, command.removeprefix("play ").strip()))

        elif command.startswith("content "):
            funcs.append(asyncio.to_thread(Content, command.removeprefix("content ").strip()))

        elif command.startswith("google search "):
            funcs.append(asyncio.to_thread(GoogleSearch, command.removeprefix("google search ").strip()))

        elif command.startswith("youtube search "):
            funcs.append(asyncio.to_thread(YouTubeSearch, command.removeprefix("youtube search ").strip()))

        elif command.startswith("system "):
            funcs.append(asyncio.to_thread(System, command.removeprefix("system ").strip()))

        elif command.startswith("reminder "):
            funcs.append(asyncio.to_thread(Reminder, command.removeprefix("reminder ").strip()))

        else:
            print(f"No Function Found. For {command}")

    results = await asyncio.gather(*funcs)
    for result in results:
        yield result


async def Automation(commands: list[str]):
    async for _result in TranslateAndExecute(commands):
        pass
    return True
