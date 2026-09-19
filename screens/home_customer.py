from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from kivy.app import App
from functions import database, file


class Home1(Screen):
    firstname = StringProperty("")
    lastname = StringProperty("")
    role = StringProperty("")
    money = StringProperty("")  # ตัวแปรสำหรับเก็บยอดเงิน

    def on_enter(self, *args):
        self.role = file.get_role()
        self.firstname = file.get_firstname()
        self.lastname = file.get_lastname()
        self.money = f"{float(file.get_money()):,.2f}"

    def go_to(self, destination):
        self.manager.current = destination

    def logout(self):
        file.clear_file()
        self.go_to("login")