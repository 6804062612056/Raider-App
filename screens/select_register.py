from kivy.uix.screenmanager import Screen

class SelectRegister(Screen):
    def go_register(self, role):
        screen = self.manager.get_screen("register")
        screen.role = role
        self.manager.current = "register"