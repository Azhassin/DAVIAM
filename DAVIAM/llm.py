"""Shared Groq chat client.

``llama3-70b-8192`` and ``mixtral-8x7b-32768`` have been removed from Groq.
The default model is the current production replacement and can be overridden
with ``GroqModel`` in ``.env``.
"""

import re

from paths import env_get

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
_THINKING = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def groq_model():
    return env_get("GroqModel", DEFAULT_GROQ_MODEL)


def groq_client():
    key = env_get("GroqAPIKey")
    if not key:
        raise RuntimeError(
            "GroqAPIKey is missing. Add it to DAVIAM/.env (see .env.example)."
        )
    from groq import Groq

    return Groq(api_key=key)


def _strip_thinking(text):
    return _THINKING.sub("", text or "").replace("</s>", "").strip()


def groq_chat(messages, max_tokens=2048, temperature=0.7):
    """Stream a chat completion and return the visible answer text."""
    client = groq_client()
    kwargs = {
        "model": groq_model(),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 1,
        "stream": True,
    }
    try:
        completion = client.chat.completions.create(**kwargs, reasoning_effort="low")
    except TypeError:
        completion = client.chat.completions.create(**kwargs)

    answer = []
    reasoning = []
    for chunk in completion:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        content = getattr(delta, "content", None)
        if content:
            answer.append(content)
        thought = getattr(delta, "reasoning", None)
        if thought:
            reasoning.append(thought)

    text = _strip_thinking("".join(answer))
    if not text:
        text = _strip_thinking("".join(reasoning))
    return text
