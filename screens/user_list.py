import threading
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty, BooleanProperty

from functions import database


class UserList(Screen):
    users = ListProperty([])
    is_loading = BooleanProperty(False)

    def on_enter(self, *args):
        # โหลดข้อมูลใน Background Thread เพื่อไม่ให้ UI สลับหน้าค้าง
        self.load_users()

    def go_to(self, destination):
        self.manager.current = destination

    def load_users(self):
        self.is_loading = True
        threading.Thread(target=self._fetch_users_async, daemon=True).start()

    def _fetch_users_async(self):
        """ดึงข้อมูลผู้ใช้จาก Supabase ใน Background Thread"""
        data = database.select_all()
        
        formatted_users = []
        if data:
            for user in data:
                rating_time = user.get('rating_time', 0)
                sum_rating = user.get('sum_rating', 0)
                rating = sum_rating / rating_time if rating_time > 0 else 0
                
                line = (
                    f"Name : {user.get('firstname', '')} {user.get('lastname', '')}\n"
                    f"Role : {user.get('role', '')}\n"
                    f"Email : {user.get('email', '')}\n"
                    f"Password : {user.get('password', '')}\n"
                    f"Money : {user.get('money', 0)}\n"
                    f"rating time : {rating_time}\n"
                    f"sum rating : {sum_rating}\n"
                    f"rating : {rating:.1f}\n\n"
                )
                formatted_users.append(line)

        # ส่งค่ากลับมาอัปเดต UI บน Main Thread ผ่าน Clock.schedule_once
        Clock.schedule_once(lambda dt: self._update_ui(formatted_users))

    def _update_ui(self, formatted_users):
        """อัปเดต UI บน Main Thread ทีเดียวทั้งหมด (Batch Update)"""
        self.users = formatted_users
        self.is_loading = False