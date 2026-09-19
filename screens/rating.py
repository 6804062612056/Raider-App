from kivy.uix.screenmanager import Screen
from kivy.properties import NumericProperty
from functions import file

class RatingScreen(Screen):
    selected_rating = NumericProperty(0)  # เริ่มต้นที่ 0 คือยังไม่เลือก

    def on_enter(self):
        """ทำงานทุกครั้งที่เปลี่ยนมาหน้าจอ Rating เพื่อเคลียร์ค่าเก่าทิ้ง"""
        self.selected_rating = 0
        print("RatingScreen entered, reset selected_rating to 0")

    def set_rating(self, rating_value):
        """ฟังก์ชันรองรับเมื่อกดเลือกตัวเลขคะแนน"""
        self.selected_rating = rating_value
        print(f"Selected rating: {rating_value}")

    def on_continue(self):
        """ปุ่ม Continue"""
        print("Continue clicked on Rating Screen")
        
        if self.selected_rating == 0:
            print("Please select a rating score first!")
            return

        role = file.get_role()
        target_email = ""

        # กำหนดเป้าหมายอีเมลตาม Role
        if role == "customer":
            # ลูกค้าให้คะแนน -> ใช้ __email ของ Rider__
            target_email = getattr(self.manager, "current_rider_email", "")
        elif role == "rider":
            # ไรเดอร์ให้คะแนน -> ใช้ __email ของ Customer__
            target_email = getattr(self.manager, "current_customer_email", "")

        # ทำการอัปเดตคะแนนผ่านฟังก์ชัน rating ใน file.py
        if target_email:
            try:
                # เรียกใช้ฟังก์ชันจาก file.py โดยตรง
                file.rating(target_email, self.selected_rating)
                print(f"Successfully updated rating for {target_email} with rate {self.selected_rating}")
            except Exception as e:
                print("Error updating rating:", e)
        else:
            print("Target email is empty, cannot update rating.")

        # เปลี่ยนหน้าจอตาม Role
        if role == "customer":
            self.manager.current = "home_customer"
        elif role == "rider":
            self.manager.current = "connect_rider"
        else:
            self.manager.current = "home_customer"