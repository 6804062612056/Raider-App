import threading
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.screenmanager import Screen
from functions import file


class RatingScreen(Screen):
    selected_rating = NumericProperty(0)
    title_text = StringProperty("Rate Your Experience")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.role = ""

    def on_enter(self):
        """ทำงานทุกครั้งที่เปลี่ยนมาหน้าจอ Rating เพื่อเคลียร์ค่าเก่าทิ้ง"""
        self.selected_rating = 0
        print("RatingScreen entered, reset selected_rating to 0")

        threading.Thread(target=self._get_role_async, daemon=True).start()

    def _get_role_async(self):
        try:
            role = file.get_role()
            Clock.schedule_once(lambda dt: self._update_role_ui(role))
        except Exception as e:
            print("Error getting role:", e)

    def _update_role_ui(self, role):
        self.role = role
        if self.role == "customer":
            self.title_text = "Rate Your Rider"
        elif self.role == "rider":
            self.title_text = "Rate Your Passenger"

    def set_rating(self, rating_value):
        """
        ถ้ากดซ้ำดาวดวงเดิมที่มีค่าเท่ากับคะแนนปัจจุบัน ให้รีเซ็ตเป็น 0
        ไม่อย่างนั้นให้เปลี่ยนเป็นคะแนนใหม่ตามที่กด
        """
        if self.selected_rating == rating_value:
            self.selected_rating = 0
        else:
            self.selected_rating = rating_value
        print(f"Selected rating: {self.selected_rating}")

    def on_continue(self):
        print("Continue clicked on Rating Screen")

        current_rating = self.selected_rating
        current_role = self.role

        target_email = ""
        if current_role == "customer":
            target_email = getattr(self.manager, "current_rider_email", "")
        elif current_role == "rider":
            target_email = getattr(self.manager, "current_customer_email", "")

        # บันทึกคะแนนลงไฟล์/ฐานข้อมูลเบื้องหลัง
        if current_rating > 0 and target_email:
            threading.Thread(
                target=self._save_rating_async,
                args=(target_email, current_rating),
                daemon=True
            ).start()
        elif current_rating > 0 and not target_email:
            print("Target email is empty, cannot update rating.")
        else:
            print("No rating selected, skipping rating update.")

        # เคลียร์ข้อมูลพิกัดและอีเมลค้างทั้งหมด ป้องกันการเด้งเข้าหน้าแผนที่เองในอนาคต
        if hasattr(self.manager, "rider_start_coords"):
            self.manager.rider_start_coords = None
        if hasattr(self.manager, "rider_dest_coords"):
            self.manager.rider_dest_coords = None
        if hasattr(self.manager, "current_rider_email"):
            self.manager.current_rider_email = None
        if hasattr(self.manager, "current_customer_email"):
            self.manager.current_customer_email = None

        # สลับหน้าจอทันที ไม่ต้องรอให้บันทึกข้อมูลเสร็จ
        if current_role == "customer":
            self.manager.current = "home_customer"
        elif current_role == "rider":
            self.manager.current = "connect_rider"
        else:
            self.manager.current = "home_customer"

    def _save_rating_async(self, target_email, rating):
        try:
            file.rating(target_email, rating)
            print(f"Successfully updated rating for {target_email} with rate {rating}")
        except Exception as e:
            print("Error updating rating:", e)