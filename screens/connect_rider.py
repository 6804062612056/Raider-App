from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color,Line
import threading
from functions import network

class BorderButton(Button):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.background_normal=""
        self.background_down=""
        self.background_color=(1,1,1,1)
        self.color=(0,0,0,1)
        with self.canvas.after:
            Color(0,0,0,1)
            self.border_line=Line(rectangle=(self.x,self.y,self.width,self.height),width=1)
        self.bind(pos=self.update_border,size=self.update_border)

    def update_border(self,*args):
        self.border_line.rectangle=(self.x,self.y,self.width,self.height)

class Connect2(Screen):
    server_started=False

    def on_enter(self):
        if self.server_started:
            return
        self.server_started=True
        network.set_request_callback(self.receive_request)
        threading.Thread(target=network.start_server,daemon=True).start()

    def on_leave(self):
        network.stop_server()
        self.server_started=False

    def receive_request(self,customer):
        Clock.schedule_once(lambda dt:self.show_request(customer))

    def show_request(self,customer):
        name=f"{customer.get('firstname','')} {customer.get('lastname','')}"
        text=f"Customer Request\n\nName: {name}\nEmail: {customer.get('email','')}\nRole: {customer.get('role','')}\nIP: {customer.get('ip','')}"
        content=BoxLayout(orientation="vertical",padding=15,spacing=15)
        label=Label(text=text,color=(0,0,0,1),halign="left",valign="middle")
        label.bind(size=lambda instance,value:setattr(instance,"text_size",value))
        button=BorderButton(text="OK",size_hint_y=None,height="50dp")
        content.add_widget(label)
        content.add_widget(button)
        popup=Popup(title="New Customer Request",content=content,size_hint=(0.85,0.5),auto_dismiss=False,background="",background_color=(1,1,1,1),title_color=(0,0,0,1),separator_color=(0,0,0,1),overlay_color=(0,0,0,0.5))
        with popup.canvas.after:
            Color(0,0,0,1)
            popup_border=Line(rectangle=(popup.x,popup.y,popup.width,popup.height),width=1)
        def update_border(*args):
            popup_border.rectangle=(popup.x,popup.y,popup.width,popup.height)
        popup.bind(pos=update_border,size=update_border)
        button.bind(on_release=popup.dismiss)
        popup.open()

    def go_to(self,screen):
        self.manager.current=screen