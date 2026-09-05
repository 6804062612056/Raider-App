from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty

from functions import database


class UserList(Screen):
    users = ListProperty([])

    def on_enter(self, *args):
        self.load_users()

    def go_to(self, destination):
        self.manager.current = destination

    def load_users(self):
        self.users = []

        data = database.select_all()

        if not data:
            return

        for user in data:
            rating = user['sum_rating'] / user['rating_time'] if user['rating_time'] > 0 else 0
            line = (
                f"Name : {user['firstname']} {user['lastname']}\n"
                f"Role : {user['role']}\n"
                f"Email : {user['email']}\n"
                f"Password : {user['password']}\n"
                f"Money : {user['money']}\n"
                f"rating time : {user['rating_time']}\n"
                f"sum rating : {user['sum_rating']}\n"
                f"rating : {rating}\n\n"
            )

            self.users.append(line)