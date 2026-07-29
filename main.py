#ตั้งค่าหน้าต่างแอป
from kivy.config import Config
Config.set("graphics", "width", "360")
Config.set("graphics", "height", "800")
Config.set("graphics", "resizable", "0")
from kivy.core.window import Window
Window.clearcolor = (1, 1, 1, 1)

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager , NoTransition

#โหลดหน้าจอ
from kivy.lang import Builder
from screens.login import Login
from screens.select_register import SelectRegister
from screens.register import Register
from screens.home import Home
from screens.user_list import UserList
Builder.load_file("components/Button1.kv")
Builder.load_file("components/Input1.kv")
Builder.load_file("screens/login.kv")
Builder.load_file("screens/select_register.kv")
Builder.load_file("screens/register.kv")
Builder.load_file("screens/home.kv")
Builder.load_file("screens/user_list.kv")

class MobileApp(App):
    def build(self):
        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(Login(name="login"))
        sm.add_widget(SelectRegister(name="select_register"))
        sm.add_widget(Register(name="register"))
        sm.add_widget(Home(name="home"))
        sm.add_widget(UserList(name="user_list"))
        sm.current = "login"   # <-- ให้เริ่มที่หน้า Login
        return sm

#run
if __name__ == "__main__":
    MobileApp().run()