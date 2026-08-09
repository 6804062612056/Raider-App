from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivy.clock import Clock
import threading
from functions import network

class RiderItem(BoxLayout):
    firstname=StringProperty("")
    lastname=StringProperty("")
    email=StringProperty("")
    role=StringProperty("")
    ip=StringProperty("")

    def accept(self):
        threading.Thread(
            target=self.send_request,
            daemon=True
        ).start()

    def send_request(self):
        success=network.send_customer_request(self.ip)
        Clock.schedule_once(
            lambda dt:self.show_result(success)
        )

    def show_result(self,success):
        if success:
            print("Request sent to:",self.ip)
        else:
            print("Request failed:",self.ip)