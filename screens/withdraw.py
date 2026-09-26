import threading
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
from functions import file


class WithdrawScreen(Screen):
    money = StringProperty("")
    message = StringProperty("")

    def on_enter(self, *args):
        self.message = ""
        if "amount_input" in self.ids:
            self.ids.amount_input.text = ""
        
        # ดึงยอดเงินปัจจุบันมาแสดงเมื่อเข้าหน้าจอ
        self.money = f"{float(file.get_money()):,.2f}"

    def process_withdraw(self, amount_str):
        """จัดการการถอนเงินแบบตอบสนองทันที (Optimistic Update)"""
        try:
            amount = float(amount_str)
            if amount <= 0:
                self.message = "Please enter an amount greater than 0"
                return

            # 1. อ่านยอดเงินปัจจุบันครั้งเดียว
            current_money = float(file.get_money())
            if amount > current_money:
                self.message = "Insufficient balance"
                return

            # 2. คำนวณยอดเงินใหม่ใน Memory และอัปเดตแสดงผลบน UI ทันที (ไม่ต้องรออ่านไฟล์ใหม่)
            new_balance = current_money - amount
            self.money = f"{new_balance:,.2f}"
            self.message = f"Successfully withdrew {amount:,.2f} THB"
            
            if "amount_input" in self.ids:
                self.ids.amount_input.text = ""

            # 3. ส่งงานบันทึกลงไฟล์ไปทำเบื้องหลัง (Background Thread) เพื่อไม่ให้ UI ค้าง
            threading.Thread(
                target=self._save_withdraw_async, 
                args=(-amount,), 
                daemon=True
            ).start()

        except ValueError:
            self.message = "Please enter a valid number"

    def _save_withdraw_async(self, amount):
        """ฟังก์ชันบันทึกไฟล์ใน Background Thread"""
        try:
            file.change_money(amount)
        except Exception as e:
            print("Error saving withdraw data:", e)

    def go_to(self, destination):
        self.manager.current = destination