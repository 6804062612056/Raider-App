from kivy.app import App
from pathlib import Path
from functions import database

def get_login_file():
    return Path(App.get_running_app().user_data_dir) / "login.txt"

def write_email(gmail):
    file = get_login_file()

    file.parent.mkdir(parents=True, exist_ok=True)

    with open(file, "w", encoding="utf-8") as f:
        f.write(gmail.strip())


def read_email():
    file = get_login_file()

    if not file.exists():
        return None

    with open(file, "r", encoding="utf-8") as f:
        gmail = f.readline().strip()

    if not gmail:
        return None

    return gmail

def clear_file():
    file = get_login_file()

    if file.exists():
        file.write_text("", encoding="utf-8")

def check_file():
    return 1 if read_email() else 0

def get_email():
    return database.search(read_email())["email"]

def get_role():
    return database.search(read_email())["role"]