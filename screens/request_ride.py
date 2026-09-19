from kivy.uix.screenmanager import Screen


class RequestRideScreen(Screen):
    def go_to(self,destination):
        self.manager.current = destination