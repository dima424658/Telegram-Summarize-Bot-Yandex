import json
import os
from telegram import Message

from config.common import HISTORY_SAVE_DIRECTORY


def get_file_name(chat_id: int) -> None:
    return f"{HISTORY_SAVE_DIRECTORY}/users_{str(chat_id)}.json"


def get_user_history(chat_id: int):
    file_name = get_file_name(chat_id)
    os.makedirs(os.path.dirname(file_name), exist_ok=True)

    try:
        with open(file_name, "r", encoding="utf-8") as file:
            users_history = json.load(file)

            if not users_history["chat_id"] or not users_history["users"]:
                users_history = {"chat_id": chat_id, "users": []}

    except FileNotFoundError:
        users_history = {"chat_id": chat_id, "users": []}

    return users_history


def save_user(chat_id: int, sender_id: int) -> None:
    file_name = get_file_name(chat_id)

    users_history = get_user_history(chat_id)
    users_history["users"] = list(set(users_history["users"] + [sender_id]))

    with open(file_name, "w", encoding="utf-8") as file:
        json.dump(users_history, file, ensure_ascii=False, indent=2)
