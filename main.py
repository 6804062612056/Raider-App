from kivy.config import Config
#หน้าต่างแอป
Config.set("graphics", "width", "360")
Config.set("graphics", "height", "800")
Config.set("graphics", "resizable", "0") #ไม่ให้ย่อขนาด

from kivy.app import App
from screens.home import HomeApp

class MobileApp(App):
    def build(self):
        return HomeApp()

if __name__ == "__main__":
    MobileApp().run()