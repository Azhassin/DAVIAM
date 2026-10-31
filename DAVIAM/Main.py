import os
import subprocess
import sys
import threading
from asyncio import run
from json import load
from time import sleep

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from Backend.Automation import Automation
from Backend.Chatbot import ChatBot
from Backend.Model import FirstLLayerDMM
from Backend.RealtimeSearchEngine import RealtimeSearchEngine
from Backend.SpeechToText import SpeechRecognition
from Backend.TextToSpeech import TextToSpeech
from Frontend.GUI import (
    AnswerModifier,
    GetAssistantStatus,
    GetMicrophoneStatus,
    GraphicalUserInterface,
    QueryModifier,
    SetAssistantStatus,
    SetMicrophoneStatus,
    ShowTextToScreen,
    TempDirectoryPath,
)
from paths import data_path, ensure_runtime_dirs, env_get, files_path

ensure_runtime_dirs()

Username = env_get("Username", "User")
Assistantname = env_get("Assistantname", "DAVIAM")
DefaultMessage = f'''User : Hello {Assistantname}, I am an intelligent individual named {Username}, your creator. How are you?
{Assistantname} : Welcome {Username}. I am {Assistantname}. I am doing well. How may I help you?
User : Who created you ?
{Assistantname} : I was created by a team of 6 intelligent individuals named {Username}.'''
subprocesses = []
Functions = ["open", "close", "play", "system", "content", "google search", "youtube search", "reminder"]


def ShowDefaultChatIfNoChats():
    path = data_path("ChatLog.json")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError:
        raw = ""
    if len(raw) < 5:
        with open(TempDirectoryPath("Database.data"), "w", encoding="utf-8") as handle:
            handle.write("")
        with open(TempDirectoryPath("Responses.data"), "w", encoding="utf-8") as handle:
            handle.write(DefaultMessage)


def ReadChatLogJson():
    with open(data_path("ChatLog.json"), "r", encoding="utf-8") as handle:
        return load(handle)


def ChatLogIntegration():
    try:
        json_data = ReadChatLogJson()
    except (OSError, ValueError):
        json_data = []
    formatted_chatlog = ""
    for entry in json_data:
        if not isinstance(entry, dict):
            continue
        content = entry.get("content", "")
        if entry.get("role") == "user":
            formatted_chatlog += f"User : {content}\n"
        elif entry.get("role") == "assistant":
            formatted_chatlog += f"{Assistantname} : {content}\n"

    with open(TempDirectoryPath("Database.data"), "w", encoding="utf-8") as handle:
        handle.write(AnswerModifier(formatted_chatlog))


def ShowChatsOnGUI():
    with open(TempDirectoryPath("Database.data"), "r", encoding="utf-8") as handle:
        Data = handle.read()
    if len(str(Data)) > 0:
        with open(TempDirectoryPath("Responses.data"), "w", encoding="utf-8") as handle:
            handle.write(Data)


def InitialExecution():
    ensure_runtime_dirs()
    SetMicrophoneStatus("False")
    ShowTextToScreen("")
    ShowDefaultChatIfNoChats()
    ChatLogIntegration()
    ShowChatsOnGUI()


def MainExecution():
    TaskExecution = False
    ImageExecution = False
    ImageGenerationQuery = ""

    SetAssistantStatus("Listening...")
    Query = SpeechRecognition()
    if not Query:
        SetAssistantStatus("Available ... ")
        return False
    ShowTextToScreen(f"User : {Query}")
    SetAssistantStatus("Thinking ... ")
    Decision = FirstLLayerDMM(Query)

    print("")
    print(f"Decision: {Decision}")
    print("")

    G = any(i for i in Decision if i.startswith("general"))
    R = any(i for i in Decision if i.startswith("realtime"))

    Mearged_query = " and ".join(
        [" ".join(i.split()[1:]) for i in Decision if i.startswith("general") or i.startswith("realtime")]
    )

    for queries in Decision:
        if queries.startswith("generate image"):
            ImageGenerationQuery = str(queries)
            ImageExecution = True

    for queries in Decision:
        if TaskExecution is False:
            if any(queries.startswith(func) for func in Functions):
                run(Automation(list(Decision)))
                TaskExecution = True

    if ImageExecution is True:
        with open(files_path("ImageGeneration.data"), "w", encoding="utf-8") as handle:
            handle.write(f"{ImageGenerationQuery},True")

        try:
            worker = subprocess.Popen(
                [sys.executable, os.path.join(ROOT, "Backend", "ImageGeneration.py")],
                cwd=ROOT,
            )
            subprocesses.append(worker)
        except Exception as error:
            print(f"Error starting ImageGeneration.py: {error}")

    if G and R:
        SetAssistantStatus("Searching ... ")
        Answer = RealtimeSearchEngine(QueryModifier(Mearged_query))
        ShowTextToScreen(f"{Assistantname} : {Answer}")
        SetAssistantStatus("Answering ... ")
        TextToSpeech(Answer)
        return True

    for Queries in Decision:
        if Queries.startswith("general"):
            SetAssistantStatus("Thinking ... ")
            QueryFinal = Queries.replace("general ", "")
            Answer = ChatBot(QueryModifier(QueryFinal))
            ShowTextToScreen(f"{Assistantname} : {Answer}")
            SetAssistantStatus("Answering ... ")
            TextToSpeech(Answer)
            return True

        elif Queries.startswith("realtime"):
            SetAssistantStatus("Searching ... ")
            QueryFinal = Queries.replace("realtime ", "")
            Answer = RealtimeSearchEngine(QueryModifier(QueryFinal))
            ShowTextToScreen(f"{Assistantname} : {Answer}")
            SetAssistantStatus("Answering ... ")
            TextToSpeech(Answer)

        elif Queries.startswith("exit"):
            QueryFinal = "Okay, Bye!"
            Answer = ChatBot(QueryModifier(QueryFinal))
            ShowTextToScreen(f"{Assistantname} : {Answer}")
            SetAssistantStatus("Answering ... ")
            TextToSpeech(Answer)
            os._exit(1)

    return True


def FirstThread():
    while True:
        CurrentStatus = GetMicrophoneStatus()

        if CurrentStatus == "True":
            MainExecution()
        else:
            AIStatus = GetAssistantStatus()

            if "Available ... " in AIStatus:
                sleep(0.1)
            else:
                SetAssistantStatus("Available ... ")


def SecondThread():
    GraphicalUserInterface()


if __name__ == "__main__":
    InitialExecution()
    thread2 = threading.Thread(target=FirstThread, daemon=True)
    thread2.start()
    SecondThread()
