from kivy.core.text import LabelBase

# ลงทะเบียนทับฟอนต์หลัก (Roboto) เพื่อบังคับใช้ทั้งแอปพลิเคชัน
LabelBase.register(
    name='Roboto',
    fn_regular='fonts/Kanit-Light.ttf',
    fn_bold='fonts/Kanit-Regular.ttf'
)

# ตั้งค่าหน้าต่างแอป
from kivy.config import Config
Config.set("graphics", "width", "360")
Config.set("graphics", "height", "800")
Config.set("graphics", "resizable", "0")
from kivy.core.window import Window
Window.clearcolor = (1, 1, 1, 1)

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from functions import file

try:
    from android.permissions import request_permissions, Permission
except ImportError:
    request_permissions = None

# โหลดหน้าจอ
from kivy.lang import Builder
from screens.login import Login
from screens.select_register import SelectRegister
from screens.register import Register
from screens.home_customer import Home1
from screens.home_rider import Home2
from screens.user_list import UserList
from screens.map import Map
from screens.connect_customer import Connect1
from screens.connect_rider import Connect2
from screens.select_location import SelectLocation
from screens.tracking_map import TrackingMap
from screens.ride_info import RideInfoScreen
from screens.deposit import DepositScreen
from screens.withdraw import WithdrawScreen
from screens.ride_fee import RideFeeScreen
from screens.rating import RatingScreen

kv_files = [
    "components/custom_widgets.kv",
    "screens/login.kv",
    "screens/select_register.kv",
    "screens/register.kv",
    "screens/home_customer.kv",
    "screens/home_rider.kv",
    "screens/user_list.kv",
    "screens/map.kv",
    "components/rider_item.kv",
    "screens/connect_customer.kv",
    "screens/connect_rider.kv",
    "screens/select_location.kv",
    "screens/tracking_map.kv",
    "screens/ride_info.kv",
    "screens/deposit.kv",
    "screens/withdraw.kv",
    "screens/ride_fee.kv",
    "screens/rating.kv"
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

        self.sm = ScreenManager(transition=FadeTransition(duration=0.25))
        
        # เพิ่ม Widget ทั้งหมดลง ScreenManager
        self.sm.add_widget(Login(name="login"))
        self.sm.add_widget(SelectRegister(name="select_register"))
        self.sm.add_widget(Register(name="register"))
        self.sm.add_widget(Home1(name="home_customer"))
        self.sm.add_widget(Home2(name="home_rider"))
        self.sm.add_widget(UserList(name="user_list"))
        self.sm.add_widget(Map(name="map"))
        self.sm.add_widget(Connect1(name="connect_customer"))
        self.sm.add_widget(Connect2(name="connect_rider"))
        self.sm.add_widget(SelectLocation(name="select_location"))
        self.sm.add_widget(TrackingMap(name="tracking_map"))
        self.sm.add_widget(RideInfoScreen(name="ride_info"))
        self.sm.add_widget(DepositScreen(name="deposit"))
        self.sm.add_widget(WithdrawScreen(name="withdraw"))
        self.sm.add_widget(RideFeeScreen(name="ride_fee"))
        self.sm.add_widget(RatingScreen(name="rating"))

        # -----------------------------------------------------------------
        # ตรวจสอบสถานะการเข้าใช้งาน
        # -----------------------------------------------------------------
        is_logged_in = file.check_file() == 1
        user_role = file.get_role() if is_logged_in else ""

        if is_logged_in:
            if user_role == "customer":
                self.sm.current = "home_customer"
            elif user_role == "rider":
                self.sm.current = "home_rider"
            else:
                self.sm.current = "login"
        else:
            self.sm.current = "login"

        Window.bind(on_keyboard=self.on_key_down)
        return self.sm

    def on_stop(self):
        """ทำงานอัตโนมัติเมื่อผู้ใช้ปิดแอป หรือปัดแอปทิ้งใน Background"""
        try:
            if hasattr(self, 'sm') and self.sm and self.sm.current_screen:
                current_screen = self.sm.current_screen
                # สั่งให้สกรีนปัจจุบันสั่งปิด Connection / Thread ดักฟัง / ส่ง Cancel ทันที
                if hasattr(current_screen, "cancel_booking_and_back"):
                    current_screen.cancel_booking_and_back()
                elif hasattr(current_screen, "stop_rider_listener"):
                    current_screen.stop_rider_listener()
                elif hasattr(current_screen, "stop_customer_listener"):
                    current_screen.stop_customer_listener()
        except Exception as e:
            print("Error cleaning up on app stop:", e)

    def on_key_down(self, window, key, *args):
        if not hasattr(self, 'sm') or not self.sm or not self.sm.current:
            return False
        
        if key == 27:  # รหัสคีย์ Back บน Android / Escape บน PC
            current_screen = self.sm.current

            main_screens = ["login", "home_customer", "home_rider", "tracking_map", "ride_info", "ride_fee", "rating"]

            if current_screen in main_screens:
                return False

            navigation_map = {
                "select_register": "login",
                "register": "select_register",
                "user_list": "login",
                "map": "user_list",
                "deposit": "home_customer",
                "withdraw": "home_rider",
                "select_location": "home_customer",
                "connect_customer": "home_customer",
                "connect_rider": "home_rider"
            }

            if current_screen in navigation_map:
                # ถ้ากดย้อนกลับจากหน้าค้นหา ให้สั่งปิด Listener เครือข่ายด้วย
                if current_screen == "connect_customer":
                    customer_screen = self.sm.get_screen("connect_customer")
                    if hasattr(customer_screen, "cancel_booking_and_back"):
                        customer_screen.cancel_booking_and_back()
                        return True
                elif current_screen == "connect_rider":
                    rider_screen = self.sm.get_screen("connect_rider")
                    if hasattr(rider_screen, "stop_rider_listener"):
                        rider_screen.stop_rider_listener()

                self.sm.current = navigation_map[current_screen]
                return True

        return False

if __name__ == "__main__":
    MobileApp().run()