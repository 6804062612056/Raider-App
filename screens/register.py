from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty

class Register(Screen):
    role = StringProperty("")

    def go_login(self):
            self.manager.current = "login"