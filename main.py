#ตั้งค่าหน้าต่างแอป
from kivy.config import Config
Config.set("graphics", "width", "360")
Config.set("graphics", "height", "800")
Config.set("graphics", "resizable", "0")
from kivy.core.window import Window
Window.clearcolor = (1, 1, 1, 1)

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager , NoTransition
from functions import file

try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None

#โหลดหน้าจอ
from kivy.lang import Builder
from screens.login import Login
from screens.select_register import SelectRegister
from screens.register import Register
from screens.home_customer import Home1
from screens.home_rider import Home2
from screens.user_list import UserList
from screens.map import Map
kv_files = [
    "components/Button1.kv",
    "components/Input1.kv",
    "screens/login.kv",
    "screens/select_register.kv",
    "screens/register.kv",
    "screens/home_customer.kv",
    "screens/home_rider.kv",
    "screens/user_list.kv",
    "screens/map.kv"
]
for data in kv_files:
    Builder.load_file(data)

class MobileApp(App):
    def build(self):
        
        if request_permissions:
                    request_permissions([
                        Permission.ACCESS_FINE_LOCATION,
                        Permission.ACCESS_COARSE_LOCATION
                    ])

        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(Login(name="login"))
        sm.add_widget(SelectRegister(name="select_register"))
        sm.add_widget(Register(name="register"))
        sm.add_widget(Home1(name="home_customer"))
        sm.add_widget(Home2(name="home_rider"))
        sm.add_widget(UserList(name="user_list"))
        sm.add_widget(Map(name="map"))
        sm.current = "login"   # <-- ให้เริ่มที่หน้า Login

        if file.check_file() == 1:
            if file.get_role() == "customer":
                sm.current = "home_customer"
            elif file.get_role() == "rider":
                sm.current = "home_rider"
        else:
            sm.current = "login"

        return sm

#run
if __name__ == "__main__":
    MobileApp().run()