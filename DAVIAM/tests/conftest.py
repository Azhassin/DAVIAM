import os

# Headless-safe defaults for the whole suite. Speech, audio playback, and
# image viewers are exercised with fakes rather than a microphone or speakers.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DAVIAM_SPEECH", "text")
os.environ.setdefault("DAVIAM_HEADLESS", "1")
