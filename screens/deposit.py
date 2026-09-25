import threading
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from functions import file


class DepositScreen(Screen):
    money = StringProperty("")
    message = StringProperty("")

    def on_enter(self, *args):
        self.message = ""
        if "amount_input" in self.ids:
            self.ids.amount_input.text = ""
        
        # ดึงยอดเงินปัจจุบันมาแสดงเมื่อเข้าหน้าจอ
        self.money = f"{float(file.get_money()):,.2f}"

    def process_deposit(self, amount_str):
        """จัดการการเติมเงินแบบตอบสนองทันที (Optimistic Update)"""
        try:
            amount = float(amount_str)
            if amount <= 0:
                self.message = "Please enter an amount greater than 0"
                return

            # 1. อ่านยอดเงินปัจจุบันและคำนวณยอดเงินใหม่ทันที
            current_money = float(file.get_money())
            new_balance = current_money + amount

            # 2. อัปเดตแสดงผลบน UI ทันทีโดยไม่ต้องรอเขียน/อ่านไฟล์ซ้ำ
            self.money = f"{new_balance:,.2f}"
            self.message = f"Successfully deposited {amount:,.2f} THB"
            
            if "amount_input" in self.ids:
                self.ids.amount_input.text = ""

            # 3. ส่งงานบันทึกลงไฟล์ไปทำเบื้องหลัง (Background Thread)
            threading.Thread(
                target=self._save_deposit_async, 
                args=(amount,), 
                daemon=True
            ).start()

        except ValueError:
            self.message = "Please enter a valid number"

    def _save_deposit_async(self, amount):
        """ฟังก์ชันบันทึกไฟล์ใน Background Thread"""
        try:
            file.change_money(amount)
        except Exception as e:
            print("Error saving deposit data:", e)

    def go_to(self, destination):
        self.manager.current = destination