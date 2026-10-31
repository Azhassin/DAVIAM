import os
import sys
from json import dump, load

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import datetime

from llm import groq_chat
from paths import data_path, env_get
from textutil import AnswerModifier


def _system_prompt():
    username = env_get("Username", "User")
    assistant = env_get("Assistantname", "DAVIAM")
    full_form = env_get("FullForm", "Dynamic Automated Virtual Interactive Assistant Model")
    return f"""Hello, I am an intelligent individual named {username}. I am the one who created you. You are a very accurate and advanced AI chatbot named {assistant}, which stands for {full_form} which also has real-time up-to-date information from the internet.
*** Do not tell time until I ask, do not talk too much, just answer the question.***
*** Reply in only English, even if the question is in any other language, reply in English.***
*** Do not provide notes in the output, just answer the question and never mention your training data. ***
"""


def _chat_log_path():
    return data_path("ChatLog.json")


def _load_messages():
    path = _chat_log_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = load(handle)
        if isinstance(data, list):
            return data
    except (OSError, ValueError):
        pass
    _save_messages([])
    return []


def _save_messages(messages):
    path = _chat_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        dump(messages, handle, indent=4)


def RealtimeInformation():
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime("%A")
    date = current_date_time.strftime("%d")
    month = current_date_time.strftime("%B")
    year = current_date_time.strftime("%Y")
    hour = current_date_time.strftime("%H")
    minute = current_date_time.strftime("%M")
    second = current_date_time.strftime("%S")

    data = "Please use this real-time information if needed,\n"
    data += f"Day: {day}\nDate: {date}\nMonth: {month}\nYear: {year}\n"
    data += f"Time: {hour} hours :{minute} minutes :{second} seconds.\n"
    return data


def ChatBot(Query):
    """Send the user's query to the chatbot and return the assistant's response."""
    try:
        messages = _load_messages()
        messages.append({"role": "user", "content": f"{Query}"})
        system = [
            {"role": "system", "content": _system_prompt()},
            {"role": "system", "content": RealtimeInformation()},
        ]
        answer = groq_chat(system + messages, max_tokens=2048)
        messages.append({"role": "assistant", "content": answer})
        _save_messages(messages)
        return AnswerModifier(Answer=answer)
    except Exception as error:
        print(f"Error: {error}")
        return "I could not answer that just now. Please check the Groq API key and try again."


if __name__ == "__main__":
    while True:
        user_input = input("Enter Your Question: ")
        print(ChatBot(user_input))
