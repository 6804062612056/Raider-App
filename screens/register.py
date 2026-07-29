from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty , BooleanProperty
from functions import auth

class Register(Screen):
    role = StringProperty("")
    error_message = StringProperty("")
    form_valid = BooleanProperty(False)

    def on_enter(self, *args):
        self.error_message = ""
        self.reset_form()

    def go_to(self,destination):
        self.manager.current = destination

    def reset_form(self):
        for widget_id in (
            "firstname",
            "lastname",
            "email",
            "password",
            "confirm_password",
        ):
            self.ids[widget_id].text = ""

    def get_data(self):
            return [
                self.ids.firstname.text.strip(),
                self.ids.lastname.text.strip(),
                self.ids.email.text.strip(),
                self.ids.password.text.strip(),
                self.ids.confirm_password.text.strip(),
                ]
         
    def check_form(self):
        self.error_message = ""
        self.form_valid = all(self.get_data())

    def register(self):
        data = self.get_data()
        flag = auth.register(self.role,data[0],data[1],data[2],data[3],data[4])
        if flag == 0:
            self.error_message = "This email is already registered."
        elif flag == 1:
            self.error_message = "Passwords do not match."
        elif flag == 2:
            self.go_to("login")