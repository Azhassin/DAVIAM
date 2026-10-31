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
    return f"""Hello, I am an intelligent individual named {username}, your creator. You are a very accurate and advanced AI chatbot named {assistant}, which stands for {full_form} which has real-time up-to-date information from the internet.
*** Provide Answers In a Professional Way, make sure to add full stops, commas, question marks, and use proper grammar.***
*** Just answer the question from the provided data in a professional way. ***"""


SystemChatBot = [
    {"role": "system", "content": _system_prompt()},
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello, how can I help you?"},
]


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
    return []


def _save_messages(messages):
    path = _chat_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        dump(messages, handle, indent=4)


def GoogleSearch(query):
    try:
        from googlesearch import search

        results = list(search(query, advanced=True, num_results=5))
    except Exception as error:
        print(f"Web search failed: {error}")
        return f"The search results for '{query}' could not be retrieved.\n"

    answer = f"The search results for '{query}' are:\n[start]\n"
    for item in results:
        title = getattr(item, "title", "") or ""
        description = getattr(item, "description", "") or ""
        answer += f"Title: {title}\nDescription: {description}\n\n"
    answer += "[end]"
    return answer


def Information():
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime("%A")
    date = current_date_time.strftime("%d")
    month = current_date_time.strftime("%B")
    year = current_date_time.strftime("%Y")
    hour = current_date_time.strftime("%H")
    minute = current_date_time.strftime("%M")
    second = current_date_time.strftime("%S")
    data = "Use this Real-time Information if needed,\n"
    data += f"Day: {day}\n"
    data += f"Date: {date}\n"
    data += f"Month: {month}\n"
    data += f"Year: {year}\n"
    data += f"Time: {hour} hours, {minute} minutes, {second} seconds.\n"
    return data


def RealtimeSearchEngine(prompt):
    global messages
    messages = _load_messages()
    messages.append({"role": "user", "content": f"{prompt}"})

    added = False
    try:
        SystemChatBot.append({"role": "system", "content": GoogleSearch(prompt)})
        added = True
        answer = groq_chat(
            SystemChatBot + [{"role": "system", "content": Information()}] + messages,
            max_tokens=2048,
        )
        answer = answer.strip()
        messages.append({"role": "assistant", "content": answer})
        _save_messages(messages)
        return AnswerModifier(Answer=answer)
    except Exception as error:
        print(f"Error: {error}")
        return "I could not look that up just now. Please check the Groq API key and try again."
    finally:
        if added and SystemChatBot:
            SystemChatBot.pop()


if __name__ == "__main__":
    while True:
        prompt = input("Enter your query: ")
        print(RealtimeSearchEngine(prompt))
