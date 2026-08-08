from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty , BooleanProperty
from functions import auth

class Login(Screen):
    error_message = StringProperty("")
    form_valid = BooleanProperty(False)

    def on_enter(self, *args):
        self.error_message = ""
        self.reset_form()

    def go_to(self,destination):
        self.manager.current = destination

    def reset_form(self):
        for widget_id in (
            "email",
            "password"
        ):
            self.ids[widget_id].text = ""

    def get_data(self):
            return [
                self.ids.email.text.strip(),
                self.ids.password.text.strip()
                ]
         
    def check_form(self):
        self.error_message = ""
        self.form_valid = all(self.get_data())

    def login_button(self):
        data = self.get_data()
        flag = auth.login(data[0],data[1])
        if flag == 0:
            self.error_message = "Invaid email or password"
        else:
            screen = self.manager.get_screen("home")
            if flag == 1:
                screen.role = "Customer"
            elif flag == 2:
                screen.role = "Rider"
            self.go_to("home")