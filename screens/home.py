from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty

class Home(Screen):
    role = StringProperty("")

    def go_to(self,destination):
        self.manager.current = destination