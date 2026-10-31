import asyncio
import datetime
import json
import os

import pytest


def test_paths_are_inside_the_project():
    from paths import ENV_FILE, ROOT, data_path, files_path, graphics_path

    assert os.path.isdir(os.path.join(ROOT, "Backend"))
    assert data_path("ChatLog.json") == os.path.join(ROOT, "Data", "ChatLog.json")
    assert files_path("Mic.data").endswith(os.path.join("Frontend", "Files", "Mic.data"))
    assert graphics_path("Jarvis.gif").endswith(os.path.join("Frontend", "Graphics", "Jarvis.gif"))
    assert ENV_FILE == os.path.join(ROOT, ".env")
    assert "\\" not in data_path("ChatLog.json") or os.name == "nt"


def test_query_modifier_handles_empty_and_questions():
    from textutil import AnswerModifier, QueryModifier

    assert QueryModifier("") == ""
    assert QueryModifier("   ") == ""
    assert QueryModifier("how are you") == "How are you?"
    assert QueryModifier("hello") == "Hello."
    assert AnswerModifier("one\n\n two \n") == "one\n two "


def test_realtime_clock_is_interpolated():
    from Backend.RealtimeSearchEngine import Information

    text = Information()
    now = datetime.datetime.now()
    assert "{date}" not in text
    assert "{month}" not in text
    assert "{year}" not in text
    assert now.strftime("%B") in text
    assert now.strftime("%Y") in text
    assert now.strftime("%d") in text


def test_parse_decisions_keeps_known_commands_only():
    from Backend.Model import parse_decisions

    parsed = parse_decisions(
        "open chrome, general tell me about mahatma gandhi., not a command"
    )
    assert parsed == ["open chrome", "general tell me about mahatma gandhi."]
    assert parse_decisions("hello there") == []
    reminder = parse_decisions(
        "general what is today's date, reminder 11:00pm 5th aug dancing performance"
    )
    assert reminder[0].startswith("general")
    assert reminder[1].startswith("reminder")


def test_decision_without_api_key_falls_back_to_general(monkeypatch):
    from Backend import Model

    monkeypatch.setattr(Model, "env_get", lambda name, default=None: default)
    assert Model.FirstLLayerDMM("how are you?") == ["general how are you?"]


def test_imports_do_not_start_chrome_or_image_worker():
    import Backend.Automation
    import Backend.Chatbot
    import Backend.ImageGeneration as images
    import Backend.Model
    import Backend.RealtimeSearchEngine
    import Backend.SpeechToText as speech
    import Backend.TextToSpeech

    assert speech._driver is None
    assert callable(images.run_worker)


def test_image_request_parsing_and_validation():
    from Backend.ImageGeneration import (
        image_from_response,
        is_image_bytes,
        normalise_prompt,
        parse_image_request,
    )

    assert parse_image_request("generate image of a red, blue bird,True") == (
        "generate image of a red, blue bird",
        "True",
    )
    assert parse_image_request("False,False") == ("False", "False")
    assert normalise_prompt("generate image of a lighthouse") == "a lighthouse"
    assert is_image_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 8)
    assert not is_image_bytes(b'{"error":"https://api-inference.huggingface.co is gone"}')

    class Response:
        status_code = 410
        content = b'{"error":"gone"}'

        def json(self):
            return {"error": "gone"}

    with pytest.raises(RuntimeError):
        image_from_response(Response())


def test_voice_page_uses_standard_speech_api(tmp_path, monkeypatch):
    import Backend.SpeechToText as speech

    monkeypatch.setattr(speech, "voice_html_path", lambda: str(tmp_path / "Voice.html"))
    monkeypatch.setattr(speech, "input_language", lambda: "en-GB")
    speech.write_voice_html()
    html = (tmp_path / "Voice.html").read_text(encoding="utf-8")
    assert "en-GB" in html
    assert "window.SpeechRecognition || window.webkitSpeechRecognition" in html
    assert "new webkitSpeechRecognition()" not in html
    assert "let listening = false" in html


def test_speech_reads_query_file_without_a_microphone(monkeypatch):
    from paths import ensure_runtime_dirs, files_path
    import Backend.SpeechToText as speech

    ensure_runtime_dirs()
    path = files_path("Query.data")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("what is python")
    monkeypatch.setattr(speech, "speech_mode", lambda: "text")
    try:
        assert speech.SpeechRecognition() == "What is python?"
        assert speech._driver is None
        with open(path, encoding="utf-8") as handle:
            assert handle.read() == ""
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_chrome_options_are_not_headless():
    selenium = pytest.importorskip("selenium")
    assert selenium is not None
    from Backend.SpeechToText import USER_AGENT, chrome_options

    arguments = " ".join(chrome_options().arguments)
    assert "--headless" not in arguments
    assert "Mozilla/5.0" in USER_AGENT
    assert "Morzilla" not in USER_AGENT


def test_chatbot_persists_success_and_keeps_history_on_failure(monkeypatch, tmp_path):
    import paths
    from Backend import Chatbot

    monkeypatch.setattr(paths, "DATA_DIR", str(tmp_path))
    existing = [{"role": "user", "content": "keep me"}]
    (tmp_path / "ChatLog.json").write_text(json.dumps(existing), encoding="utf-8")

    def fail(messages, max_tokens=2048, temperature=0.7):
        raise RuntimeError("invalid api key")

    monkeypatch.setattr(Chatbot, "groq_chat", fail)
    result = Chatbot.ChatBot("hello")
    assert "Groq" in result
    saved = json.loads((tmp_path / "ChatLog.json").read_text(encoding="utf-8"))
    assert saved == existing

    monkeypatch.setattr(Chatbot, "groq_chat", lambda *args, **kwargs: "Four.")
    assert Chatbot.ChatBot("what is two plus two?") == "Four."
    saved = json.loads((tmp_path / "ChatLog.json").read_text(encoding="utf-8"))
    assert saved[-1] == {"role": "assistant", "content": "Four."}
    assert saved[0]["content"] == "keep me"


def test_realtime_search_does_not_leak_search_context(monkeypatch, tmp_path):
    import paths
    from Backend import RealtimeSearchEngine as search

    monkeypatch.setattr(paths, "DATA_DIR", str(tmp_path))
    (tmp_path / "ChatLog.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(search, "GoogleSearch", lambda query: "Title: Example\n")
    before = len(search.SystemChatBot)

    monkeypatch.setattr(search, "groq_chat", lambda *args, **kwargs: "The answer is 42.")
    assert search.RealtimeSearchEngine("who won") == "The answer is 42."
    assert len(search.SystemChatBot) == before

    def explode(*args, **kwargs):
        raise RuntimeError("nope")

    monkeypatch.setattr(search, "groq_chat", explode)
    message = search.RealtimeSearchEngine("news today")
    assert "Groq" in message
    assert len(search.SystemChatBot) == before


def test_automation_routes_commands_without_opening_apps(monkeypatch):
    from Backend import Automation

    monkeypatch.setenv("DAVIAM_DRY_RUN", "1")
    Automation.performed.clear()
    commands = [
        "open chrome",
        "open it",
        "close notepad",
        "play jazz",
        "content a short poem",
        "google search cats",
        "youtube search music",
        "system volume up",
        "reminder 9:00pm call home",
        "general hello",
    ]
    assert asyncio.run(Automation.Automation(commands)) is True
    kinds = [kind for kind, _detail in Automation.performed]
    assert sorted(kinds) == sorted([
        "open",
        "close",
        "play",
        "content",
        "google search",
        "youtube search",
        "system",
        "reminder",
    ])


def test_tts_saves_audio_when_playback_is_unavailable(monkeypatch, tmp_path):
    import Backend.TextToSpeech as tts

    destination = tmp_path / "speech.mp3"
    monkeypatch.setattr(tts, "speech_path", lambda: str(destination))

    class FakeCommunicator:
        def __init__(self, text, voice, pitch="+0Hz", rate="+0%"):
            self.text = text

        async def save(self, path):
            with open(path, "wb") as handle:
                handle.write(b"ID3fake-audio")

    monkeypatch.setattr(tts.edge_tts, "Communicate", FakeCommunicator)

    class Mixer:
        @staticmethod
        def init():
            raise RuntimeError("no audio device")

        @staticmethod
        def get_init():
            return None

    monkeypatch.setattr(tts, "pygame", type("Pygame", (), {"mixer": Mixer})())
    assert tts.TTS("Hello there.") is True
    assert destination.read_bytes().startswith(b"ID3")


def test_long_reply_is_shortened_for_speech(monkeypatch):
    import Backend.TextToSpeech as tts

    captured = {}

    def fake(text, func=lambda r=None: True):
        captured["text"] = text
        return True

    monkeypatch.setattr(tts, "TTS", fake)
    sentences = ". ".join(f"This is a fairly long sentence number {index}" for index in range(12))
    assert len(sentences) >= 250
    assert tts.TextToSpeech(sentences) is True
    assert "chat screen" in captured["text"]
    assert len(captured["text"]) < len(sentences)


def test_chat_log_formatting_does_not_rewrite_message_text(monkeypatch, tmp_path):
    import paths
    import Main

    monkeypatch.setattr(paths, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(Main, "TempDirectoryPath", lambda name: str(tmp_path / name))
    monkeypatch.setattr(Main, "Assistantname", "DAVIAM")
    (tmp_path / "ChatLog.json").write_text(json.dumps([
        {"role": "user", "content": "Username stays intact"},
        {"role": "assistant", "content": "Assistant is the role"},
    ]), encoding="utf-8")
    Main.ChatLogIntegration()
    text = (tmp_path / "Database.data").read_text(encoding="utf-8")
    assert "User : Username stays intact" in text
    assert "DAVIAM : Assistant is the role" in text
    assert "User name" not in text


def test_main_routes_chat_and_automation(monkeypatch):
    import Main

    spoken = {}
    shown = []
    monkeypatch.setattr(Main, "SpeechRecognition", lambda: "What is two plus two?")
    monkeypatch.setattr(Main, "FirstLLayerDMM", lambda query: ["general what is two plus two?"])
    monkeypatch.setattr(Main, "ChatBot", lambda query: "Four.")
    monkeypatch.setattr(Main, "TextToSpeech", lambda text, func=None: spoken.setdefault("text", text))
    monkeypatch.setattr(Main, "SetAssistantStatus", lambda status: None)
    monkeypatch.setattr(Main, "ShowTextToScreen", lambda text: shown.append(text))
    assert Main.MainExecution() is True
    assert spoken["text"] == "Four."
    assert any(line.startswith("User :") for line in shown)

    called = {}

    async def fake_auto(commands):
        called["commands"] = commands
        return True

    monkeypatch.setattr(Main, "SpeechRecognition", lambda: "Open notepad.")
    monkeypatch.setattr(Main, "FirstLLayerDMM", lambda query: ["open notepad"])
    monkeypatch.setattr(Main, "Automation", fake_auto)
    assert Main.MainExecution() is True
    assert called["commands"] == ["open notepad"]

    monkeypatch.setattr(Main, "SpeechRecognition", lambda: "")
    assert Main.MainExecution() is False


def test_main_queues_image_generation(monkeypatch):
    import Main
    from paths import files_path

    started = {}

    class Process:
        pass

    def fake_popen(args, cwd=None):
        started["args"] = args
        started["cwd"] = cwd
        return Process()

    monkeypatch.setattr(Main.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(Main, "SpeechRecognition", lambda: "Draw a lighthouse.")
    monkeypatch.setattr(Main, "FirstLLayerDMM", lambda query: ["generate image of a lighthouse"])
    monkeypatch.setattr(Main, "SetAssistantStatus", lambda status: None)
    monkeypatch.setattr(Main, "ShowTextToScreen", lambda text: None)
    monkeypatch.setattr(Main, "TextToSpeech", lambda text, func=None: None)
    original = open(files_path("ImageGeneration.data"), encoding="utf-8").read()
    try:
        Main.MainExecution()
        queued = open(files_path("ImageGeneration.data"), encoding="utf-8").read()
        assert queued == "generate image of a lighthouse,True"
        assert started["args"][0]
        assert started["args"][1].endswith(os.path.join("Backend", "ImageGeneration.py"))
        assert started["cwd"] == Main.ROOT
    finally:
        with open(files_path("ImageGeneration.data"), "w", encoding="utf-8") as handle:
            handle.write(original)


def test_gui_constructs_offscreen_and_mic_toggle_is_file_backed():
    pytest.importorskip("PyQt5")
    from PyQt5.QtWidgets import QApplication
    import sys

    from paths import ensure_runtime_dirs, files_path

    ensure_runtime_dirs()
    status_path = files_path("Status.data")
    mic_path = files_path("Mic.data")
    original_status = open(status_path, encoding="utf-8").read()
    original_mic = open(mic_path, encoding="utf-8").read()
    app = QApplication.instance() or QApplication(sys.argv)
    try:
        from Frontend.GUI import MainWindow, SetAssistantStatus

        window = MainWindow()
        window.show()
        app.processEvents()
        stacked = window.centralWidget()
        home = stacked.widget(0)
        assert home is not None
        assert stacked.count() == 2
        home.toggle_icon()
        assert open(mic_path, encoding="utf-8").read() == "True"
        SetAssistantStatus("Listening...")
        home.SpeechRecogText()
        assert home.label.text() == "Listening..."
        window.close()
    finally:
        with open(status_path, "w", encoding="utf-8") as handle:
            handle.write(original_status)
        with open(mic_path, "w", encoding="utf-8") as handle:
            handle.write(original_mic)
