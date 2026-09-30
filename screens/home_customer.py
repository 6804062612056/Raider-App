import threading
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from functions import database, file


class Home1(Screen):
    firstname = StringProperty("")
    lastname = StringProperty("")
    role = StringProperty("")
    money = StringProperty("0.00")  # ตัวแปรสำหรับเก็บยอดเงิน

    # ตัวแประดับ Class สำหรับทำ Cache ข้อมูลผู้ใช้งาน
    _cached_email = None
    _cached_role = ""
    _cached_fname = ""
    _cached_lname = ""
    _cached_money = "0.00"

    def on_enter(self, *args):
        current_email = file.read_email()

        # 1. กรณีเป็นผู้ใช้คนเดิม และมี Cache อยู่แล้ว -> แสดงผลทันที
        if Home1._cached_email and Home1._cached_email == current_email:
            self.role = Home1._cached_role
            self.firstname = Home1._cached_fname
            self.lastname = Home1._cached_lname
            self.money = Home1._cached_money

            # รัน Background Thread เพื่อเช็กยอดเงินล่าสุดใน Database
            threading.Thread(
                target=self._refresh_money_async,
                args=(current_email,),
                daemon=True
            ).start()
            return

        # 2. กรณีสลับบัญชี หรือยังไม่มี Cache -> ขึ้น Loading แล้วอ่านไฟล์เบื้องหลัง
        self.firstname = "Loading..."
        self.lastname = ""
        self.money = "0.00"

        threading.Thread(
            target=self._load_user_data_async, 
            args=(current_email,), 
            daemon=True
        ).start()

    def _refresh_money_async(self, current_email):
        """เช็กยอดเงินล่าสุดจาก Database เบื้องหลังเพื่ออัปเดตแบบ Real-time"""
        try:
            user_db = database.search(current_email) if current_email else {}
            if user_db and "money" in user_db:
                raw_money = float(user_db.get("money", 0))
                money_str = f"{raw_money:,.2f}"

                # ถ้ายอดเงินเปลี่ยนไปจาก Cache ให้อัปเดต UI และ Cache ใหม่ทันที
                if money_str != Home1._cached_money:
                    Home1._cached_money = money_str
                    Clock.schedule_once(lambda dt: setattr(self, "money", money_str))
        except Exception as e:
            print("Error refreshing money from DB:", e)

    def _load_user_data_async(self, current_email):
        """ดึงข้อมูลผู้ใช้เบื้องหลังเฉพาะตอนเปลี่ยนบัญชี"""
        try:
            role_val = file.get_role()
            fname_val = file.get_firstname()
            lname_val = file.get_lastname()

            # ดึงยอดเงินจาก Database โดยตรง
            user_db = database.search(current_email) if current_email else {}
            if user_db and "money" in user_db:
                raw_money = float(user_db.get("money", 0))
            else:
                try:
                    raw_money = float(file.get_money())
                except Exception:
                    raw_money = 0.0

            money_str = f"{raw_money:,.2f}"

            # บันทึกลง Cache ไว้ใช้ในครั้งถัดไป
            Home1._cached_email = current_email
            Home1._cached_role = role_val
            Home1._cached_fname = fname_val
            Home1._cached_lname = lname_val
            Home1._cached_money = money_str

            # ส่งกลับไปอัปเดต UI บน Main Thread
            Clock.schedule_once(
                lambda dt: self._update_ui(role_val, fname_val, lname_val, money_str)
            )
        except Exception as e:
            print("Error loading user data in Home1:", e)

    def _update_ui(self, role_val, fname_val, lname_val, money_str):
        self.role = role_val
        self.firstname = fname_val
        self.lastname = lname_val
        self.money = money_str

    @classmethod
    def clear_cache(cls):
        """ล้าง Cache ข้อมูลผู้ใช้ทั้งหมด"""
        cls._cached_email = None
        cls._cached_role = ""
        cls._cached_fname = ""
        cls._cached_lname = ""
        cls._cached_money = "0.00"

    def go_to(self, destination):
        self.manager.current = destination

    def logout(self):
        # ล้าง Cache เมื่อผู้ใช้กด Logout
        Home1.clear_cache()
        threading.Thread(target=file.clear_file, daemon=True).start()
        self.go_to("login")