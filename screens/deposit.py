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
        
        # ดึงยอดเงินปัจจุบันผ่าน file.get_money() มาแสดง
        self.money = f"{float(file.get_money()):,.2f}"

    def process_deposit(self, amount_str):
        """จัดการการเติมเงินโดยเรียกผ่าน file.change_money()"""
        try:
            amount = float(amount_str)
            if amount <= 0:
                self.message = "Please enter an amount greater than 0"
                return

            # เรียกใช้ฟังก์ชัน change_money จาก file.py เพื่อบวกเงินเพิ่ม
            file.change_money(amount)
            self.money = f"{float(file.get_money()):,.2f}"
            
            self.message = f"Successfully deposited {amount:,.2f} THB"
            
            if "amount_input" in self.ids:
                self.ids.amount_input.text = ""

        except ValueError:
            self.message = "Please enter a valid number"

    def go_to(self, destination):
        self.manager.current = destination