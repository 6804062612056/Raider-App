from kivy.uix.screenmanager import Screen

class Login(Screen):
    def go_select_register(self):
        self.manager.current = "select_register"

    def go_home(self):
        self.manager.current = "home"