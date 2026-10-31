import asyncio
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import edge_tts

from paths import data_path, env_get

try:
    import pygame
except Exception as error:
    pygame = None
    print(f"pygame is unavailable, so speech will be saved but not played: {error}")

DEFAULT_VOICE = "en-US-JennyNeural"


def speech_path():
    return data_path("speech.mp3")


def assistant_voice():
    return env_get("AssistantVoice", DEFAULT_VOICE)


async def TextToAudioFile(text) -> None:
    file_path = speech_path()
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if os.path.exists(file_path):
        os.remove(file_path)

    communicate = edge_tts.Communicate(text, assistant_voice(), pitch="+5Hz", rate="+13%")
    await communicate.save(file_path)


def _prefer_dummy_audio():
    """Avoid opening a missing sound card. SDL then plays to a silent driver."""
    if os.environ.get("SDL_AUDIODRIVER"):
        return False
    if os.environ.get("DAVIAM_HEADLESS") == "1":
        return True
    return sys.platform.startswith("linux") and not os.path.isdir("/dev/snd")


def _play_audio(file_path, func):
    if pygame is None:
        print(f"Saved speech to {file_path}. Playback was skipped because pygame is unavailable.")
        return True

    if _prefer_dummy_audio():
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        print("No speakers detected. The reply was saved and will not be played aloud.")

    try:
        pygame.mixer.init()
    except Exception as error:
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        try:
            pygame.mixer.init()
        except Exception:
            print(f"Audio playback is unavailable ({error}). Speech was saved to {file_path}.")
            return True
        print(f"Audio playback is unavailable ({error}). Speech was saved to {file_path}.")

    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        if func() is False:
            break
        pygame.time.Clock().tick(10)
    return True


def TTS(Text, func=lambda r=None: True):
    try:
        asyncio.run(TextToAudioFile(Text))
    except Exception as error:
        print(f"Error in TTS: {error}")
        return False

    file_path = speech_path()
    try:
        return _play_audio(file_path, func)
    except Exception as error:
        print(f"Audio playback is unavailable ({error}). Speech was saved to {file_path}.")
        return True
    finally:
        try:
            func(False)
            if pygame is not None and pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.quit()
        except Exception as error:
            print(f"Error in finally block: {error}")


def TextToSpeech(Text, func=lambda r=None: True):
    Data = str(Text).split(".")

    responses = [
        "The rest of the result has been printed to the chat screen, kindly check it out sir.",
        "The rest of the text is now on the chat screen, sir, please check it.",
        "You can see the rest of the text on the chat screen, sir.",
        "The remaining part of the text is now on the chat screen, sir.",
        "Sir, you'll find more text on the chat screen for you to see.",
        "The rest of the answer is now on the chat screen, sir.",
        "Sir, please look at the chat screen, the rest of the answer is there.",
        "You'll find the complete answer on the chat screen, sir.",
        "The next part of the text is on the chat screen, sir.",
        "Sir, please check the chat screen for more information.",
        "There's more text on the chat screen for you, sir.",
        "Sir, take a look at the chat screen for additional text.",
        "You'll find more to read on the chat screen, sir.",
        "Sir, check the chat screen for the rest of the text.",
        "The chat screen has the rest of the text, sir.",
        "There's more to see on the chat screen, sir, please look.",
        "Sir, the chat screen holds the continuation of the text.",
        "You'll find the complete answer on the chat screen, kindly check it out sir.",
        "Please review the chat screen for the rest of the text, sir.",
        "Sir, look at the chat screen for the complete answer.",
    ]

    if len(Data) > 4 and len(Text) >= 250:
        spoken = " ".join(Text.split(".")[0:2]) + ". " + random.choice(responses)
        return TTS(spoken, func)

    return TTS(Text, func)


if __name__ == "__main__":
    while True:
        TextToSpeech(input("Enter the text: "))
