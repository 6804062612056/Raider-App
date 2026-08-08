from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from kivy.app import App
from functions import database, file


class Home1(Screen):
    email = StringProperty("")
    role = StringProperty("")

    def on_enter(self, *args):
        self.role = file.get_role()
        self.email = file.get_email()

    def go_to(self, destination):
        self.manager.current = destination

    def logout(self):
        file.clear_file()
        self.go_to("login")