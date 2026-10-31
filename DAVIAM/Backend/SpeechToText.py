import os
import sys
import time
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from paths import env_get, files_path, data_path
from textutil import QueryModifier

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_driver = None
_driver_failed = False


def input_language():
    return env_get("InputLanguage", "en-US")


def voice_html_path():
    return data_path("Voice.html")


def query_file_path():
    return files_path("Query.data")


def speech_mode():
    """How speech input is collected.

    ``auto`` uses Chrome only when a display is available. Headless Chrome
    cannot run the Web Speech API, so servers and this kind of VM fall back
    to typed text or ``Frontend/Files/Query.data``.
    """
    mode = (env_get("DAVIAM_SPEECH", "auto") or "auto").strip().lower()
    if mode in {"text", "browser"}:
        return mode
    if os.environ.get("DAVIAM_HEADLESS") == "1":
        return "text"
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return "text"
    return "browser"


def SetAssistantStatus(Status):
    path = files_path("Status.data")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(Status)


def write_voice_html():
    language = input_language().replace("\\", "").replace("'", "")
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <title>Speech Recognition</title>
</head>
<body>
    <button id="start" onclick="startRecognition()">Start Recognition</button>
    <button id="end" onclick="stopRecognition()">Stop Recognition</button>
    <p id="output"></p>
    <script>
        const output = document.getElementById('output');
        let recognition;
        let listening = false;

        function startRecognition() {{
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRec) {{
                output.textContent = "";
                return;
            }}
            recognition = new SpeechRec();
            recognition.lang = '{language}';
            recognition.continuous = true;

            recognition.onresult = function(event) {{
                const transcript = event.results[event.results.length - 1][0].transcript;
                output.textContent += transcript;
            }};

            recognition.onend = function() {{
                if (listening) {{
                    try {{
                        recognition.start();
                    }} catch (error) {{}}
                }}
            }};
            listening = true;
            recognition.start();
        }}

        function stopRecognition() {{
            listening = false;
            if (recognition) {{
                recognition.stop();
            }}
            output.innerHTML = "";
        }}
    </script>
</body>
</html>'''
    path = voice_html_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(html)
    return path


def chrome_options():
    from selenium.webdriver.chrome.options import Options

    options = Options()
    options.add_argument(f"user-agent={USER_AGENT}")
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--use-fake-device-for-media-stream")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return options


def get_driver():
    global _driver, _driver_failed
    if _driver is not None:
        return _driver
    if _driver_failed:
        raise RuntimeError("Chrome speech recognition is unavailable.")

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        service = Service(ChromeDriverManager().install())
        _driver = webdriver.Chrome(service=service, options=chrome_options())
        return _driver
    except Exception as error:
        _driver_failed = True
        raise RuntimeError(f"Could not start Chrome for speech recognition: {error}") from error


def UniversalTranslator(Text):
    import mtranslate as mt

    english_translation = mt.translate(Text, "en", "auto")
    return english_translation.capitalize()


def _finish_transcript(text):
    language = input_language().lower()
    if language == "en" or language.startswith("en"):
        return QueryModifier(text)
    SetAssistantStatus("Translating...")
    return QueryModifier(UniversalTranslator(text))


def _consume_query_file():
    path = query_file_path()
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read().strip()
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("")
    return text or None


def _text_listen():
    queued = _consume_query_file()
    if queued:
        return _finish_transcript(queued)
    if sys.stdin is not None and sys.stdin.isatty():
        try:
            typed = input("You: ")
        except EOFError:
            return ""
        return _finish_transcript(typed)
    return ""


def _browser_listen(timeout=60):
    from selenium.webdriver.common.by import By

    write_voice_html()
    driver = get_driver()
    driver.get(Path(voice_html_path()).resolve().as_uri())
    driver.find_element(by=By.ID, value="start").click()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            text = driver.find_element(by=By.ID, value="output").text
            if text:
                driver.find_element(by=By.ID, value="end").click()
                return _finish_transcript(text)
        except Exception:
            pass
        time.sleep(0.2)
    return ""


def SpeechRecognition():
    queued = _consume_query_file()
    if queued:
        return _finish_transcript(queued)

    if speech_mode() == "text":
        return _text_listen()

    try:
        return _browser_listen()
    except Exception as error:
        print(f"Speech recognition fell back to text input: {error}")
        return _text_listen()


if __name__ == "__main__":
    while True:
        print(SpeechRecognition())
