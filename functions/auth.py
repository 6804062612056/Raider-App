from kivy.app import App
from pathlib import Path
#FILE = Path(__file__).resolve().parent.parent / "users.txt"

def get_file():
    return Path(App.get_running_app().user_data_dir) / "users.txt"

def load_users():
    users = {}
    FILE = get_file()

    # ถ้ายังไม่มีไฟล์ก็สร้างไฟล์เปล่า
    FILE.parent.mkdir(parents=True, exist_ok=True)
    if not FILE.exists():
        FILE.touch()

    with open(FILE, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 5:
                usertype, firstname, lastname, email, password = parts
                users[email] = [usertype, firstname, lastname, password]

    return users    #{'MikeWazowski@mail.com': ['rider', 'Mike', 'Wazowski', '123']}


def register(usertype, firstname, lastname, email,password,confirm): #usertype เช่น customer,rider
    FILE = get_file()

    # กรณีตอนกรอก username และ password มี whitespace
    firstname = firstname.strip()
    lastname = lastname.strip()
    email = email.strip()
    password = password.strip()
    confirm = confirm.strip()

    users = load_users()

    if password != confirm: #เช็คว่า password ตรงกับ confirm password ไหม
        return 1

    if email in users: #เช็คว่ามีชื่อซ้ำไหม
        return 0

    #เขียนลงไฟล์ ex. customer,firstname,lastname,user1@mail,1234 แล้วขึ้นบรรทัดใหม่
    with open(FILE, "a") as f:
        f.write(f"{usertype},{firstname},{lastname},{email},{password}\n")
        return 2

def login(email,password):

    # กรณีตอนกรอก username และ password มี whitespace
    email = email.strip()
    password = password.strip()

    #อ่านไฟล์
    users = load_users()

    if email in users: #ถ้ามี mail ในไฟล์
        if password == users[email][3]: #ถ้า password ถูก
            if users[email][0] == "Customer": #ถ้าเป็น customer
                return 1
            elif users[email][0] == "Rider": #ถ้าเป็น rider
                return 2
        else: #ถ้ามี mail ในไฟล์ แต่ password ผิด
            return 0
    else: #ถ้าไม่มี mail ในไฟล์
        return 0
    
def main():
    register("Rider","Mike","Wazowski","MikeWazowski@mail.com","123","123")
    print(login("unknown","none"))
    print(login("MikeWazowski@mail.com","123"))