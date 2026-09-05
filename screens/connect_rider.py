import json
import socket
import threading
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.properties import ListProperty, StringProperty
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen

from functions import network, file, database  # เพิ่ม database เข้ามาใช้งาน


class BorderButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (1, 1, 1, 1)
        self.color = (0, 0, 0, 1)
        with self.canvas.after:
            Color(0, 0, 0, 1)
            self.border_line = Line(
                rectangle=(self.x, self.y, self.width, self.height), width=1
            )
        self.bind(pos=self.update_border, size=self.update_border)

    def update_border(self, *args):
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)


class Connect2(Screen):
    server_started = False
    result_text = StringProperty("Waiting for customers...")
    subnets_text = StringProperty("Listening for real-time customer requests...")
    customers = ListProperty([])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sock = None
        self.is_listening = False

    def on_enter(self):
        network.acquire_android_multicast_lock()
        self.result_text = "Waiting for customers..."
        self.subnets_text = "Listening for real-time customer requests..."
        self.customers = []
        if hasattr(self.ids, "customer_list"):
            self.ids.customer_list.clear_widgets()

        if not self.is_listening:
            self.start_realtime_listener()

    def on_leave(self):
        self.stop_realtime_listener()

    def start_realtime_listener(self):
        self.is_listening = True
        threading.Thread(
            target=self.listen_thread, name="RiderRealtimeListener", daemon=True
        ).start()

    def stop_realtime_listener(self):
        self.is_listening = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def listen_thread(self):
        """ไรเดอร์ฟังพอร์ต 5000 เพื่อรอรับคำขอจากลูกค้า"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("", 5000))
            self.sock.settimeout(1.0)
        except Exception as e:
            print("Socket bind error (Rider):", e)
            return

        while self.is_listening:
            try:
                if not self.sock:
                    break
                    
                data, addr = self.sock.recvfrom(1024)
                if not data:
                    continue
                
                message = json.loads(data.decode("utf-8"))
                
                # กรองรับเฉพาะแพ็กเกจ BOOK_REQUEST จากลูกค้าเท่านั้น
                if message.get("type") != "BOOK_REQUEST":
                    continue

                customer_ip = addr[0]
                customer_email = message.get("email", "")
                
                # คำนวณเรตติ้งจาก Database ของลูกค้าคนนี้โดยตรงเพื่อให้ได้ทศนิยม 1 ตำแหน่งที่แม่นยำ
                calculated_rating = 0.0
                if customer_email:
                    try:
                        cust_db_data = database.search(customer_email)
                        if cust_db_data:
                            sum_r = cust_db_data.get("sum_rating", 0)
                            time_r = cust_db_data.get("rating_time", 0)
                            if time_r > 0:
                                calculated_rating = sum_r / time_r
                    except Exception as err:
                        print("Error fetching customer rating from database:", err)
                
                customer_data = {
                    "ip": customer_ip,
                    "email": customer_email,
                    "firstname": message.get("firstname", "Customer"),
                    "lastname": message.get("lastname", ""),
                    "rating": calculated_rating,  # ใช้ค่าเรตติ้งที่คำนวณแบบทศนิยม
                    "start_lat": message.get("start_lat"),
                    "start_lon": message.get("start_lon"),
                    "dest_lat": message.get("dest_lat"),
                    "dest_lon": message.get("dest_lon")
                }

                Clock.schedule_once(lambda dt, c=customer_data: self.add_or_update_customer(c))

            except socket.timeout:
                continue
            except Exception as e:
                if not self.is_listening:
                    break
                print("Listener error (Rider):", e)
                break

        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def add_or_update_customer(self, customer):
        """ป้องกันไม่ให้ชื่อหรืออีเมลซ้ำกัน แม้จะส่งมาคนละ IP ก็จะยุบรวมเป็นรายการเดียว"""
        c_email = customer.get("email", "").strip()
        c_name = f"{customer.get('firstname', '').strip()} {customer.get('lastname', '').strip()}".lower()
        
        existing_index = -1
        for i, c in enumerate(self.customers):
            existing_email = c.get("email", "").strip()
            existing_name = f"{c.get('firstname', '').strip()} {c.get('lastname', '').strip()}".lower()
            
            if (c_email and existing_email and c_email == existing_email) or (c_name and existing_name and c_name == existing_name):
                existing_index = i
                break

        if existing_index != -1:
            self.customers[existing_index] = customer
        else:
            self.customers.append(customer)

        self.refresh_customer_list()

    def refresh_customer_list(self):
        if hasattr(self.ids, "customer_list"):
            self.ids.customer_list.clear_widgets()

        if not self.customers:
            self.result_text = "Waiting for customers..."
            return

        self.result_text = f"Found {len(self.customers)} Customer(s) (Real-time)"

        for customer in self.customers:
            name = f"{customer.get('firstname', '')} {customer.get('lastname', '')}".strip() or "Customer"
            
            # ดึง Rating และจัดรูปแบบให้แสดงผลเป็นทศนิยม 1 ตำแหน่ง (.1f)
            try:
                rating = float(customer.get("rating", 0))
            except (ValueError, TypeError):
                rating = 0.0
            
            # ปุ่มแสดงชื่อลูกค้าและ Rating รูปแบบทศนิยม 1 ตำแหน่ง
            item = BorderButton(
                text=f"{name} (Rating: {rating:.1f})",
                size_hint_y=None,
                height="50dp"
            )
            item.bind(on_release=lambda instance, c=customer: self.select_customer(c))
            
            if hasattr(self.ids, "customer_list"):
                self.ids.customer_list.add_widget(item)

    def select_customer(self, customer):
        """เมื่อไรเดอร์เลือกชื่อลูกค้า ให้เก็บบันทึกข้อมูลลง manager แล้วพาไปหน้า ride_info เพื่อดูรายละเอียดก่อน"""
        customer_ip = customer.get("ip")
        if not customer_ip:
            self.result_text = "Error: Invalid Customer IP"
            return

        self.manager.selected_customer_ip = customer_ip
        
        start_lat = customer.get("start_lat")
        start_lon = customer.get("start_lon")
        dest_lat = customer.get("dest_lat")
        dest_lon = customer.get("dest_lon")

        if start_lat and start_lon:
            self.manager.rider_start_coords = (float(start_lat), float(start_lon))
        if dest_lat and dest_lon:
            self.manager.rider_dest_coords = (float(dest_lat), float(dest_lon))

        self.manager.current = "ride_info"

    def go_to(self, screen):
        self.manager.current = screen