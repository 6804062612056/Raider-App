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

def get_money():
    return database.search(read_email())["money"]

def get_firstname():
    return database.search(read_email())["firstname"]

def get_lastname():
    return database.search(read_email())["lastname"]

def get_rating():
    user = database.search(read_email())
    return user['sum_rating'] / user['rating_time'] if user['rating_time'] > 0 else 0

def change_money(money):
    email = read_email()
    print("DEBUG EMAIL:", repr(email)) # พิมพ์ดูว่าค่าที่อ่านได้จากไฟล์คืออะไร
    if email:
        current_money = float(database.search(email).get("money", 0))
        new_money = current_money + float(money)
        database.update_column(email, "money", new_money)

def rating(email,rate):
    new_rating_time = database.search(email)["rating_time"] + 1
    new_sum_rating = database.search(email)["sum_rating"] + rate
    database.update_column(email, "rating_time", new_rating_time)
    database.update_column(email, "sum_rating", new_sum_rating)