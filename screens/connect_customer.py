from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty,ListProperty
from kivy.clock import Clock
import threading
from functions import network
from components.rider_item import RiderItem

class Connect1(Screen):
    result_text=StringProperty("Press SCAN to find Riders")
    riders=ListProperty([])

    def scan(self):
        self.result_text="Scanning..."
        self.riders=[]
        self.ids.rider_list.clear_widgets()
        threading.Thread(target=self.do_scan,daemon=True).start()

    def do_scan(self):
        try:
            users=network.scan_network()
            riders=[user for user in users if user.get("role","").lower()=="rider"]
            Clock.schedule_once(lambda dt:self.show_riders(riders))
        except Exception as e:
            Clock.schedule_once(lambda dt:self.show_error(str(e)))

    def show_riders(self,riders):
        self.riders=riders
        self.ids.rider_list.clear_widgets()
        if not riders:
            self.result_text="No Riders found"
            return
        self.result_text=f"Found {len(riders)} Rider(s)"
        for rider in riders:
            item=RiderItem(firstname=rider.get("firstname",""),lastname=rider.get("lastname",""),email=rider.get("email",""),role=rider.get("role",""),ip=rider.get("ip",""))
            self.ids.rider_list.add_widget(item)

    def show_error(self,error):
        self.result_text=f"Error: {error}"

    def go_to(self,screen):
        self.manager.current=screen