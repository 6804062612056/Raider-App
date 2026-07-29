from kivy.uix.screenmanager import Screen


class Home(Screen):
    def go_login(self):
            self.manager.current = "login"