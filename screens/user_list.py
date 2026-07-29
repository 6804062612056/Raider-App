from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty
from functions import auth

class UserList(Screen):
    users = ListProperty()

    def on_enter(self, *args):
        self.load_users()

    def go_to(self,destination):
        self.manager.current = destination

    def load_users(self):
        self.users = []
        FILE = auth.get_file()

        if not FILE.exists():
            return

        with FILE.open("r", encoding="utf-8") as file:
            for data in file:
                data = data.strip().split(",")
                line = data[1] + " " + data[2] + "\nRole : " + data[0] + "\nEmail : " + data[3] + "\nPassword : " + data[4] + "\n\n"
                self.users.append(line)

    def clear_users(self):
        FILE = auth.get_file()

        with open(FILE, "w", encoding="utf-8"):
            pass

        self.users = []